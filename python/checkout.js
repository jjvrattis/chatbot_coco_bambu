// ================================================
// CHECKOUT ABACATEPAY - MARMIRATRIA
// Gera PIX QR Code para pagamentos
// ================================================

require('dotenv').config();
const https = require('https');

// Pega API key do .env
const ABACATEPAY_API_KEY = process.env.AbacatePay_API_Key;

// Mapeamento de produtos e preços (em centavos)
const PRODUTOS = {
  'baiao de dois': { nome: 'Baião de Dois Completo', preco: 2890 },
  'baião de dois': { nome: 'Baião de Dois Completo', preco: 2890 },
  'frango ao molho pardo': { nome: 'Frango ao Molho Pardo com Angu', preco: 2650 },
  'frango molho pardo': { nome: 'Frango ao Molho Pardo com Angu', preco: 2650 },
  'pirarucu a casaca': { nome: 'Pirarucu à Casaca', preco: 3290 },
  'pirarucu à casaca': { nome: 'Pirarucu à Casaca', preco: 3290 },
  'virado paulista': { nome: 'Virado à Paulista', preco: 3090 },
  'virado à paulista': { nome: 'Virado à Paulista', preco: 3090 },
  'arroz de carreteiro': { nome: 'Arroz de Carreteiro', preco: 2790 },
  'arroz carreteiro': { nome: 'Arroz de Carreteiro', preco: 2790 },
};

/**
 * Gera um CPF válido aleatório
 * @returns {string} CPF no formato 11 dígitos
 */
function gerarCpfValido() {
  // Gera 9 primeiros dígitos aleatórios
  const cpf = [];
  for (let i = 0; i < 9; i++) {
    cpf.push(Math.floor(Math.random() * 10));
  }

  // Calcula primeiro dígito verificador
  let soma = 0;
  for (let i = 0; i < 9; i++) {
    soma += cpf[i] * (10 - i);
  }
  let d1 = 11 - (soma % 11);
  d1 = d1 > 9 ? 0 : d1;
  cpf.push(d1);

  // Calcula segundo dígito verificador
  soma = 0;
  for (let i = 0; i < 10; i++) {
    soma += cpf[i] * (11 - i);
  }
  let d2 = 11 - (soma % 11);
  d2 = d2 > 9 ? 0 : d2;
  cpf.push(d2);

  return cpf.join('');
}

/**
 * Cria um PIX QR Code via AbacatePay
 * @param {string} produtoNome - Nome do produto
 * @param {number} valorCentavos - Valor em centavos
 * @param {string} clienteNome - Nome do cliente
 * @param {string} clienteTelefone - Telefone do cliente
 * @param {string} clienteEmail - Email do cliente
 * @param {string} clienteCpf - CPF do cliente (será gerado aleatório se vazio)
 * @returns {Promise<Object>} Dados do PIX criado
 */
async function criarPixCheckout(
  produtoNome,
  valorCentavos,
  clienteNome = 'Cliente',
  clienteTelefone = '',
  clienteEmail = 'cliente@email.com',
  clienteCpf = '',
  expiresSeconds = 3600
) {

  if (!ABACATEPAY_API_KEY) {
    throw new Error('AbacatePay_API_Key não encontrada no .env');
  }

  // Gerar CPF válido aleatório se não fornecido
  if (!clienteCpf || clienteCpf.trim() === '') {
    clienteCpf = gerarCpfValido();
    console.error(`CPF gerado automaticamente: ${clienteCpf}`);
  }

  const descricao = `Marmiratria - ${produtoNome}`;

  const payload = JSON.stringify({
    amount: valorCentavos,
    expiresIn: parseInt(expiresSeconds || 3600, 10),
    description: descricao,
    customer: {
      name: clienteNome,
      cellphone: clienteTelefone || '(11) 00000-0000',
      email: clienteEmail,
      taxId: clienteCpf
    },
    metadata: {
      produto: produtoNome,
      valor_reais: (valorCentavos / 100).toFixed(2)
    }
  });
*/
*/

  const options = {
    hostname: 'api.abacatepay.com',
    port: 443,
    path: '/v1/pixQrCode/create',
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${ABACATEPAY_API_KEY}`,
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload)
    }
  };

  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });
*/

      res.on('end', () => {
        if (res.statusCode === 200 || res.statusCode === 201) {
          try {
            const response = JSON.parse(data);
            const pixData = response.data || response;

            resolve({
              success: true,
              qr_code_url: pixData.brCodeBase64 || pixData.qrCodeUrl || null,
              pix_copia_cola: pixData.brCode || pixData.qrCode || null,
              valor: valorCentavos / 100,
              produto: produtoNome,
              id: pixData.id,
              expires_at: pixData.expiresAt || pixData.expires_at,
              platform_fee: pixData.platformFee,
              customer_id: pixData.customerId
            });
          } catch (error) {
            reject(new Error(`Erro ao parsear resposta: ${error.message}`));
          }
        } else {
          reject(new Error(`Erro API: ${res.statusCode} - ${data}`));
        }
      });
    });

    req.on('error', (error) => {
      reject(new Error(`Erro na requisição: ${error.message}`));
    });

    req.write(payload);
    req.end();
  });
}

/**
 * Obtém informações do produto
 * @param {string} nomeProduto - Nome do produto (case insensitive)
 * @returns {Object|null} Dados do produto ou null se não encontrado
 */
function obterProduto(nomeProduto) {
  const nome = nomeProduto.toLowerCase().trim();
  return PRODUTOS[nome] || null;
}

/**
 * Formata valor em centavos para string R$ XX,XX
 * @param {number} centavos - Valor em centavos
 * @returns {string} Valor formatado
 */
function formatarPreco(centavos) {
  return `R$ ${(centavos / 100).toFixed(2).replace('.', ',')}`;
}

// ================================================
// EXPORTS
// ================================================
export {
  criarPixCheckout,
  obterProduto,
  formatarPreco,
  PRODUTOS
};

