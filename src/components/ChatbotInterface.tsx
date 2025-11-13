import { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Copy, Check } from 'lucide-react';
import { cn } from '../lib/utils';
import { io, Socket } from 'socket.io-client';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  pixData?: {
    pix_copia_cola: string;
    qr_code_url: string;
    valor: string;
    produto: string;
  };
}

export default function ChatbotInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(true);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [copiedPix, setCopiedPix] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [avatarOk, setAvatarOk] = useState(true);
  const BOT_AVATAR_URL = '/coco-bambu.png';
  const genId = (): string =>
    (typeof crypto !== 'undefined' && 'randomUUID' in crypto)
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

  // Auto scroll para a última mensagem
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (inputRef.current) inputRef.current.focus();
  }, []);

  // Configurar Socket.io
  useEffect(() => {
    console.log('Iniciando conexão WebSocket...');
    const newSocket = io('http://localhost:3001', {
      transports: ['websocket', 'polling'],
      withCredentials: true
    });
    setSocket(newSocket);

    newSocket.on('connect', () => {
      console.log('✅ Conectado ao servidor');
      setIsConnected(true);
      setIsConnecting(false);
      if (inputRef.current) inputRef.current.focus();
    });

    newSocket.on('disconnect', () => {
      console.log('❌ Desconectado do servidor');
      setIsConnected(false);
      setIsConnecting(false);
    });

    newSocket.on('connect_error', (error) => {
      console.log('❌ Erro de conexão:', error);
      setIsConnected(false);
      setIsConnecting(false);
    });

    newSocket.on('bot-response', (data) => {
      const botMessage: Message = {
        id: genId(),
        text: data.message,
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
      setIsLoading(false);
      if (inputRef.current) inputRef.current.focus();
    });

    newSocket.on('pix-data', (data) => {
      const rawQr = data.qr_code_url;
      const finalQr = rawQr
        ? (typeof rawQr === 'string' && (rawQr.startsWith('http') || rawQr.startsWith('data:'))
            ? rawQr
            : `data:image/png;base64,${rawQr}`)
        : '';
      const pixMessage: Message = {
        id: genId(),
        text: `✅ PIX gerado com sucesso!\n\n📦 ${data.produto}\n💰 Valor: R$ ${data.valor}`,
        sender: 'bot',
        timestamp: new Date(),
        pixData: { ...data, qr_code_url: finalQr }
      };
      setMessages(prev => [...prev, pixMessage]);
      setIsLoading(false);
      if (inputRef.current) inputRef.current.focus();
    });

    newSocket.on('bot-error', (data) => {
      const errorMessage: Message = {
        id: genId(),
        text: `❌ ${data.error}`,
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      setIsLoading(false);
    });

    // Mensagem inicial
    const initialMessage: Message = {
      id: genId(),
      text: "👋 E aí, amigo! Sou a Dra. Julia do Coco Bambu!\n\nO que vai ser hoje?\n[1] Ver cardápio\n[2] Promoções\n[3] Já sei o que quero\n[4] Informações",
      sender: 'bot',
      timestamp: new Date()
    };
    setMessages([initialMessage]);

    return () => {
      newSocket.close();
    };
  }, []);

  const sendMessage = () => {
    console.log('Tentando enviar mensagem - isLoading:', isLoading, 'isConnected:', isConnected, 'socket:', !!socket, 'inputMessage:', inputMessage);
    if (!inputMessage.trim() || !socket || isLoading) return;

    // Verificar se é comando menu para voltar ao início
    if (inputMessage.toLowerCase() === 'menu') {
      setMessages([{
        id: genId(),
        text: "👋 E aí, amigo! Sou a Julia do Coco Bambu!\nO que vai ser hoje?",
        sender: 'bot',
        timestamp: new Date()
      }]);
      setInputMessage('');
      return;
    }

    const userMessage: Message = {
      id: genId(),
      text: inputMessage,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    if (inputRef.current) inputRef.current.focus();

    // Enviar mensagem via Socket.io
    socket.emit('chat-message', { message: inputMessage });
  };

  const sendQuick = (text: string) => {
    if (!socket || isLoading || !text.trim()) return;
    const userMessage: Message = {
      id: genId(),
      text,
      sender: 'user',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    socket.emit('chat-message', { message: text });
    if (inputRef.current) inputRef.current.focus();
  };

  const hasInfoOptions = (text: string) => {
    const t = (text || '').toLowerCase();
    return t.includes('quer ver o cardápio') || t.includes('digite 1 para ver o cardápio');
  };

  const copyPixCode = async (pixCode: string) => {
    try {
      await navigator.clipboard.writeText(pixCode);
      setCopiedPix(true);
      setTimeout(() => setCopiedPix(false), 2000);
    } catch (error) {
      console.error('Erro ao copiar PIX:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="h-screen bg-gradient-to-bl from-[#CC9D57] via-[#F7F3EA] to-white flex flex-col">
      {/* Header */}
      <div className="bg-transparent p-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-full bg-[#DNCB98] border border-[#CC9D57]/40">
              {avatarOk ? (
                <img
                  src={BOT_AVATAR_URL}
                  alt="Coco Bambu"
                  className="w-8 h-8 rounded-full object-contain"
                  onError={() => setAvatarOk(false)}
                />
              ) : (
                <Bot className="w-8 h-8 text-[#CC9D57]" />
              )}
            </div>
            <div>
              <h1 className="text-[#3E1110] text-xl font-bold">Julia</h1>
              <p className="text-[#3E1110] text-sm">Coco Bambu</p>
            </div>
          </div>
        </div>
      </div>

      {/* Área de mensagens com autoroll */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-transparent">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                'flex items-start space-x-3',
                message.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''
              )}
            >
              <div className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                message.sender === 'bot' 
                  ? 'bg-[#DNCB98] border border-[#CC9D57]/40' 
                  : 'bg-[#CC9D57]'
              )}>
                {message.sender === 'bot' ? (
                  avatarOk ? (
                    <img
                      src={BOT_AVATAR_URL}
                      alt="Coco Bambu"
                      className="w-6 h-6 rounded-full object-contain"
                      onError={() => setAvatarOk(false)}
                    />
                  ) : (
                    <Bot className="w-4 h-4 text-[#CC9D57]" />
                  )
                ) : (
                  <User className="w-4 h-4 text-[#3E1110]" />
                )}
              </div>
              
              <div className={cn(
                'rounded-2xl px-4 py-3 max-w-md lg:max-w-lg',
                message.sender === 'bot'
                  ? 'bg-[#3E1110] text-[#CC9D57] border border-[#CC9D57]/40'
                  : 'bg-[#CC9D57] text-[#3E1110]'
              )}>
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {message.text}
                </div>

                {message.sender === 'bot' && hasInfoOptions(message.text) && (
                  <div className="mt-3 flex items-center gap-2">
                    <button
                      onClick={() => sendQuick('1')}
                      className="px-3 py-2 rounded-md text-sm bg-[#CC9D57] text-[#3E1110] hover:brightness-110 transition-colors"
                    >
                      Ver cardápio
                    </button>
                    <button
                      onClick={() => sendQuick('2')}
                      className="px-3 py-2 rounded-md text-sm bg-[#CC9D57] text-[#3E1110] hover:brightness-110 transition-colors"
                    >
                      Promoções
                    </button>
                  </div>
                )}
                
                {/* Renderizar PIX Data */}
                {message.pixData && (
                  <div className="mt-4 space-y-4 p-4 bg-[#3E1110] rounded-xl border border-[#CC9D57]/40">
                    {/* QR Code */}
                    {message.pixData.qr_code_url && (
                      <div className="text-center">
                        <img 
                          src={message.pixData.qr_code_url} 
                          alt="QR Code PIX"
                          className="mx-auto w-48 h-48 rounded-lg border-2 border-[#CC9D57]/50"
                        />
                        <p className="text-xs text-[#CC9D57]/80 mt-2">Escaneie o QR Code</p>
                      </div>
                    )}
                    
                    {/* PIX Copia e Cola */}
                    {message.pixData.pix_copia_cola && (
                      <div className="space-y-2">
                        <p className="text-sm font-medium">PIX Copia e Cola:</p>
                        <div className="bg-[#3E1110] p-3 rounded-lg border border-[#CC9D57]/40">
                          <code className="text-xs break-all">
                            {message.pixData.pix_copia_cola}
                          </code>
                        </div>
                        <button
                          onClick={() => copyPixCode(message.pixData!.pix_copia_cola)}
                          className={cn(
                            "w-full py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-center space-x-2",
                            copiedPix 
                              ? "bg-[#CC9D57] text-[#3E1110]"
                              : "bg-[#CC9D57] text-[#3E1110]"
                          )}
                        >
                          {copiedPix ? (
                            <>
                              <Check className="w-4 h-4" />
                              <span>Copiado!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-4 h-4" />
                              <span>Copiar PIX</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}
                    
                    {/* Informações do PIX */}
                    <div className="text-center text-xs">
                      <p>Produto: {message.pixData.produto}</p>
                      <p>Valor: R$ {message.pixData.valor}</p>
                      <p className="mt-2">⚠️ PIX válido por 1 hora</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex items-start space-x-3">
            <div className="w-8 h-8 rounded-full bg-[#3E1110] border border-[#CC9D57]/40 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-[#CC9D57]" />
              </div>
              <div className="bg-[#3E1110] rounded-2xl px-4 py-3 text-[#CC9D57] border border-[#CC9D57]/40">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-[#CC9D57] rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-[#CC9D57] rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <div className="w-2 h-2 bg-[#CC9D57] rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input centralizado na parte inferior */}
      <div className="bg-transparent p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex space-x-3">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Digite sua mensagem... (ou 'menu' para voltar ao início)"
              disabled={false}
              autoFocus
              ref={inputRef}
              className="flex-1 px-4 py-3 bg-[#3E1110] border border-[#CC9D57]/40 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#CC9D57] focus:border-transparent text-[#CC9D57] placeholder-[#CC9D57]/60 disabled:bg-[#3E1110] transition-all duration-200"
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !isConnected || !inputMessage.trim()}
              className={cn(
                'px-4 py-3 rounded-xl font-medium transition-all duration-200',
                isLoading || !isConnected || !inputMessage.trim()
                  ? 'bg-[#CC9D57]/50 text-[#3E1110] cursor-not-allowed'
                  : 'bg-[#CC9D57] text-[#3E1110] hover:brightness-110 transform hover:scale-105'
              )}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}