# Chatbot Marmiratria - Interface Web

Interface web moderna para o chatbot da Marmiratria, integrado com WhatsApp e sistema de pedidos via Python.

## 🚀 Tecnologias Utilizadas

- **Frontend**: React 18 + TypeScript + Tailwind CSS
- **Backend**: Node.js + Express + TypeScript + Socket.io
 - **Integração**: Python Flask (`python/App.py`)
- **Deploy**: Vercel

## 📋 Funcionalidades

- 💬 Chat em tempo real com interface moderna
- 📱 Integração com WhatsApp via Evolution API
- 🍽️ Sistema de pedidos com cardápio digital
- 💰 Pagamento via PIX (integração AbacatePay)
- 🛵 Rastreamento de pedidos e entregas
- 📊 Dashboard administrativo (em desenvolvimento)

## 🛠️ Instalação e Configuração

### Pré-requisitos

- Node.js 18+
- Python 3.8+ (para o backend Python existente)
- Conta na Evolution API
- Chave de API do AbacatePay (para PIX)

### 1. Clone o repositório

```bash
git clone [seu-repositorio]
cd Chatbot_IA
```

### 2. Configure as variáveis de ambiente

Copie o arquivo `.env.example` para `.env` e configure:

```bash
cp .env.example .env
```

Configure as variáveis:

```env
# Backend Node.js
PYTHON_API_URL=http://localhost:8001
NODE_ENV=development

# Backend Python (se ainda não configurou)
EVOLUTION_API_URL=sua_url_evolution_api
EVOLUTION_INSTANCE_NAME=nome_da_instancia
API_KEY_EVOLUTION=sua_chave_api
NOTION_API_KEY=sua_chave_notion (opcional)
ABACATEPAY_API_KEY=sua_chave_abacatepay
```

### 3. Instale as dependências

```bash
pnpm install
```

### 4. Execute o backend Python (se ainda não estiver rodando)

```bash
# Em outro terminal
python python/App.py
```

### 5. Execute o projeto

#### Desenvolvimento (ambos frontend e backend)
```bash
pnpm dev:full
```

#### Ou execute separadamente:
```bash
# Terminal 1 - Backend Node.js
pnpm server

# Terminal 2 - Frontend React
pnpm dev
```

## 📁 Estrutura do Projeto

```
Chatbot_IA/
├── api/                    # Backend Node.js
│   └── server.ts          # Servidor Express + Socket.io
├── src/
│   ├── components/         # Componentes React
│   │   └── ChatbotInterface.tsx
│   ├── pages/            # Páginas
│   │   └── Home.tsx
│   └── lib/              # Utilitários
│       └── utils.ts
├── public/                # Arquivos estáticos
├── python/               # Backend Python
│   ├── App.py            # Servidor Flask
│   └── bot_simples.py    # Lógica do chatbot
├── package.json          # Dependências Node.js
├── tsconfig.json         # Config TypeScript frontend
├── tsconfig.server.json  # Config TypeScript backend
├── vite.config.ts        # Config Vite
└── vercel.json           # Config deploy Vercel
```

## 🚀 Deploy na Vercel

### 1. Configure o projeto na Vercel

1. Acesse [vercel.com](https://vercel.com)
2. Importe seu repositório GitHub
3. Configure as variáveis de ambiente na interface da Vercel

### 2. Configure as variáveis de ambiente no painel da Vercel

```env
PYTHON_API_URL=https://seu-backend-python.vercel.app  # ou URL do seu servidor Python
NODE_ENV=production
```

### 3. Deploy automático

O deploy será feito automaticamente a cada push na branch main.

## 🔧 Desenvolvimento

### Comandos úteis

```bash
# Desenvolvimento completo (frontend + backend)
pnpm dev:full

# Apenas frontend
pnpm dev

# Apenas backend
pnpm server

# Build para produção
pnpm build

# Verificar tipos TypeScript
pnpm check

# Lint
pnpm lint
```

### Testar a integração

1. Acesse `http://localhost:5173`
2. Digite seu número de WhatsApp (formato: 5511999999999)
3. Envie uma mensagem para testar o fluxo
4. O bot responderá com o menu e poderá processar pedidos

## 📞 Fluxo de Conversa

1. **Saudação**: O bot se apresenta como Dra. Julia
2. **Menu Principal**: 
   - [1] Ver cardápio
   - [2] Promoções
   - [3] Já sei o que quero
   - [4] Informações
3. **Escolha do Prato**: Selecione um dos 4 pratos disponíveis
4. **Confirmação**: Confirme o pedido
5. **Endereço**: Forneça endereço de entrega
6. **Pagamento**: Escolha entre PIX ou Dinheiro
7. **Finalização**: Receba confirmação do pedido

## 🍽️ Cardápio

- **Baião de Dois Completo** - R$ 28,90
- **Frango ao Molho Pardo com Angu** - R$ 26,50
- **Pirarucu à Casaca** - R$ 32,90
- **Virado à Paulista** - R$ 30,90

## 💡 Personalização

### Adicionar novos pratos

Edite o arquivo `python/bot_simples.py` e modifique o dicionário `CARDAPIO`:

```python
CARDAPIO = {
    "1": {"nome": "Novo Prato", "preco": 2990},
    # ... outros pratos
}
```

### Modificar mensagens

As mensagens do bot estão nos métodos da classe `BotSimples` em `python/bot_simples.py`.

## 🐛 Troubleshooting

### Problemas comuns

1. **Backend Python não conecta**: Verifique se `python/App.py` está rodando na porta 8001
2. **CORS errors**: Verifique as configurações de CORS no backend
3. **Variáveis de ambiente**: Certifique-se de que todas as variáveis estão configuradas
4. **Portas em uso**: Verifique se as portas 5173 (frontend) e 3001 (backend) estão livres

### Verificar integração

Teste os endpoints:

```bash
# Testar backend Node.js
curl http://localhost:3001/health

# Testar backend Python
curl http://localhost:8001/health

# Testar integração
curl -X POST http://localhost:3001/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá", "phoneNumber": "5511999999999"}'
```

## 📄 Licença

Este projeto é privado e pertence à Marmiratria.

## 📞 Suporte

Para suporte técnico, entre em contato com o desenvolvedor responsável.