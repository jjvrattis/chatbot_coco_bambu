import express from 'express';
import cors from 'cors';
import axios from 'axios';
import { createServer } from 'http';
import { Server } from 'socket.io';

const app = express();
const server = createServer(app);
const io = new Server(server, {
  cors: {
    origin: process.env.NODE_ENV === 'production'
      ? ['https://your-domain.vercel.app']
      : ['http://localhost:5173', 'http://localhost:5174'],
    methods: ['GET', 'POST'],
    credentials: true
  }
});

const PORT = process.env.PORT || 3001;
const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:8001';

app.use(cors({
  origin: process.env.NODE_ENV === 'production'
    ? ['https://your-domain.vercel.app']
    : ['http://localhost:5173', 'http://localhost:5174'],
  methods: ['GET', 'POST'],
  credentials: true
}));
app.use(express.json());

// Rotas da API
app.get('/health', (req, res) => {
  res.json({ status: 'ok', message: 'Backend Node.js rodando' });
});

app.post('/api/chat/message', async (req, res) => {
  try {
    const { message } = req.body;
    
    // Usar um número fixo para identificar a sessão web
    const phoneNumber = 'web-user-001';
    
    if (!message) {
      return res.status(400).json({ 
        error: 'Mensagem é obrigatória' 
      });
    }

    // Enviar mensagem para o Python backend
    console.log('Enviando para Python:', { message, phoneNumber });
    const response = await axios.post(`${PYTHON_API_URL}/bot-simples`, {
      event: 'message',
      data: {
        body: message,
        from: phoneNumber,
        type: 'message'
      }
    });

    console.log('Resposta do Python:', response.data);
    const { reply, status } = response.data;
    
    if (status === 'success') {
      res.json({ 
        message: reply,
        status: 'success'
      });
    } else {
      res.status(500).json({ 
        error: 'Erro ao processar mensagem',
        details: response.data 
      });
    }

  } catch (error) {
    console.error('Erro ao enviar mensagem:', error);
    res.status(500).json({ 
      error: 'Erro ao processar mensagem',
      details: error instanceof Error ? error.message : 'Erro desconhecido' 
    });
  }
});

// WebSocket para chat em tempo real
io.on('connection', (socket) => {
  console.log('Cliente conectado:', socket.id);
  
  socket.on('chat-message', async (data) => {
    try {
      const { message } = data;
      
      // Usar um número fixo para identificar a sessão web
      const phoneNumber = 'web-user-001';
      
      // Enviar para Python backend
      console.log('WebSocket - Enviando para Python:', { message, phoneNumber });
      const response = await axios.post(`${PYTHON_API_URL}/bot-simples`, {
        event: 'message',
        data: {
          body: message,
          from: phoneNumber,
          type: 'message'
        }
      });

      console.log('WebSocket - Resposta do Python:', response.data);
      const { reply, status } = response.data;
      
      if (status === 'success') {
        // Verificar se é uma mensagem de PIX (GERAR_PIX)
        if (reply && reply.startsWith('GERAR_PIX:')) {
          console.log('WebSocket - Detectado GERAR_PIX, chamando endpoint de PIX...');
          
          // Extrair dados do pedido
          const dadosResponse = await axios.get(`${PYTHON_API_URL}/obter-dados-pix/${phoneNumber}`);
          console.log('WebSocket - Dados do pedido:', dadosResponse.data);
          
          if (dadosResponse.data.status === 'success') {
            const dados = dadosResponse.data.data;
            
            // Chamar endpoint de gerar PIX
            const pixResponse = await axios.post(`${PYTHON_API_URL}/gerar-pix`, {
              produto: dados.produto,
              valor_centavos: dados.valor_centavos,
              cliente_nome: dados.cliente_nome || 'Cliente',
              cliente_telefone: phoneNumber,
              cliente_cpf: dados.cliente_cpf || '',
              numero_whatsapp: phoneNumber
            });
            
            console.log('WebSocket - Resposta do PIX:', pixResponse.data);
            
            if (pixResponse.data.success) {
              // Enviar mensagem inicial do PIX
              socket.emit('bot-response', {
                message: `✅ *PIX gerado com sucesso!*\\n\\n📦 ${dados.produto}\\n💰 Valor: R$ ${(dados.valor_centavos / 100).toFixed(2)}\\n\\n🔢 *Copia e Cola e QR Code:*`,
                status: 'success'
              });
              
              // Enviar dados do PIX para renderização
              socket.emit('pix-data', {
                pix_copia_cola: pixResponse.data.pix_data.pix_copia_cola,
                qr_code_url: pixResponse.data.pix_data.qr_code_url,
                valor: (dados.valor_centavos / 100).toFixed(2),
                produto: dados.produto
              });
            } else {
              socket.emit('bot-response', {
                message: '❌ Erro ao gerar PIX. Tente novamente.',
                status: 'error'
              });
            }
          }
        } else {
          // Se a resposta do Python já trouxer dados de PIX, emitir diretamente
          const pixData = (response.data as any).pix_data;
          if (pixData && (pixData.pix_copia_cola || pixData.qr_code_url)) {
            socket.emit('pix-data', {
              pix_copia_cola: pixData.pix_copia_cola,
              qr_code_url: pixData.qr_code_url,
              valor: pixData.valor?.toFixed ? pixData.valor.toFixed(2) : String(pixData.valor),
              produto: pixData.produto
            });
          }
          // Resposta normal
          socket.emit('bot-response', {
            message: reply,
            status: 'success'
          });
        }
      } else {
        socket.emit('bot-error', {
          error: 'Erro ao processar mensagem',
          details: response.data
        });
      }
      
    } catch (error) {
      console.error('Erro no WebSocket:', error);
      socket.emit('bot-error', {
        error: 'Erro ao processar mensagem',
        details: error instanceof Error ? error.message : 'Erro desconhecido'
      });
    }
  });

  socket.on('disconnect', () => {
    console.log('Cliente desconectado:', socket.id);
  });
});

server.listen(PORT, () => {
  console.log(`🚀 Servidor rodando na porta ${PORT}`);
  console.log(`📝 Python API URL: ${PYTHON_API_URL}`);
});

export default app;