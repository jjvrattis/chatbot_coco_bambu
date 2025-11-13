"""
Bot Simples com IF/ELSE - Sem IA
Sistema de estados para fluxo de pedidos

Complementos:
- Integração com AbacatePay para gerar PIX (via API HTTP)
- Validação de CPF e geração automática de PIX no fluxo
"""
import re
import os
import random
from typing import Dict, Optional
import requests
from dotenv import load_dotenv
try:
    from notion_client import Client
except Exception:
    Client = None

load_dotenv()
NOTION_API_KEY = (
    os.getenv("NOTION_API_KEY")
    or os.getenv("Notion_API_Key")
    or os.getenv("notion_api_key")
)

# CARDÁPIO FIXO
CARDAPIO = {
    "1": {"nome": "Baião de Dois Completo", "preco": 2890},
    "2": {"nome": "Frango ao Molho Pardo com Angu", "preco": 2650},
    "3": {"nome": "Pirarucu à Casaca", "preco": 3290},
    "4": {"nome": "Virado à Paulista", "preco": 3090},
}

# Estados da conversa
ESTADOS = {
    "INICIO": "inicio",
    "MENU_PRINCIPAL": "menu_principal",
    "ESCOLHENDO_PRATO": "escolhendo_prato",
    "CONFIRMANDO_PEDIDO": "confirmando_pedido",
    "PEDINDO_ENDERECO": "pedindo_endereco",
    "PEDINDO_PAGAMENTO": "pedindo_pagamento",
    "PEDINDO_CPF": "pedindo_cpf",
    "TROCO": "troco",
    "FINALIZADO": "finalizado",
}

class BotSimples:
    def __init__(self):
        self.conversas = {}  # {numero: {estado, prato_escolhido, endereco, etc}}

    def processar_mensagem(self, numero: str, mensagem: str) -> str:
        """Processa mensagem do cliente e retorna resposta"""
        mensagem = mensagem.strip().lower()

        # Mensagens de áudio (marcador vindo do App.py)
        if mensagem == "[audio_message]":
            return "Opa! Não consigo escutar áudios ainda 🎧. Pode escrever pra mim? 😊"

        # Comando menu - voltar ao início de qualquer estado
        if mensagem in ["menu", "voltar", "inicio", "início"]:
            # Resetar conversa para o estado inicial
            self.conversas[numero] = {
                "estado": ESTADOS["INICIO"],
                "prato": None,
                "endereco": None,
                "pagamento": None,
                "cpf": None,
            }
            return self._saudacao(numero)

        # Inicializar conversa se não existir
        if numero not in self.conversas:
            self.conversas[numero] = {
                "estado": ESTADOS["INICIO"],
                "prato": None,
                "endereco": None,
                "pagamento": None,
                "cpf": None,
            }

        estado_atual = self.conversas[numero]["estado"]

        # MÁQUINA DE ESTADOS
        if estado_atual == ESTADOS["INICIO"]:
            if mensagem:
                self.conversas[numero]["estado"] = ESTADOS["MENU_PRINCIPAL"]
                return self._menu_principal(numero, mensagem)
            return self._saudacao(numero)

        elif estado_atual == ESTADOS["MENU_PRINCIPAL"]:
            return self._menu_principal(numero, mensagem)

        elif estado_atual == ESTADOS["ESCOLHENDO_PRATO"]:
            return self._escolher_prato(numero, mensagem)

        elif estado_atual == ESTADOS["CONFIRMANDO_PEDIDO"]:
            return self._confirmar_pedido(numero, mensagem)

        elif estado_atual == ESTADOS["PEDINDO_ENDERECO"]:
            return self._pedir_endereco(numero, mensagem)

        elif estado_atual == ESTADOS["PEDINDO_PAGAMENTO"]:
            return self._pedir_pagamento(numero, mensagem)

        elif estado_atual == ESTADOS["PEDINDO_CPF"]:
            return self._pedir_cpf(numero, mensagem)

        elif estado_atual == ESTADOS["TROCO"]:
            return self._troco(numero, mensagem)

        elif estado_atual == ESTADOS["FINALIZADO"]:
            self.conversas[numero] = {
                "estado": ESTADOS["MENU_PRINCIPAL"],
                "prato": None,
                "endereco": None,
                "pagamento": None,
                "cpf": None,
            }
            return self._menu_principal(numero, mensagem)

        else:
            print(f"DEBUG: Estado inválido: {estado_atual}")
            return "Desculpe, algo deu errado. Digite 'menu' para recomeçar."

    def processar_mensagem_com_pix(self, numero: str, mensagem: str) -> str:
        """Processa mensagem e, quando o fluxo solicitar, gera o PIX automaticamente.
        - Se o retorno for 'GERAR_PIX:<numero>', chama gerar_pix e retorna a mensagem de pagamento.
        - Caso contrário, retorna a resposta normal do fluxo.
        """
        resposta = self.processar_mensagem(numero, mensagem)
        if resposta.startswith("GERAR_PIX:"):
            try:
                return self.gerar_pix(numero)
            except Exception as e:
                return f"❌ Falha ao gerar PIX: {e}"
        return resposta

    def _saudacao(self, numero: str) -> str:
        """Estado inicial"""
        self.conversas[numero]["estado"] = ESTADOS["MENU_PRINCIPAL"]
        return (
            "👋 E aí, amigo! Sou a Julia do Coco Bambu!\n"

            "O que vai ser hoje?\n"
            "[1] Ver cardápio\n"
            "[2] Promoções\n"
            "[3] Já sei o que quero\n"
            "[4] Informações"
        )

    def _menu_principal(self, numero: str, mensagem: str) -> str:
        """Menu principal - Lógica corrigida conforme especificações"""
        if mensagem in ["1", "cardapio", "cardápio", "ver cardapio"]:
            # Opção 1: Mostra apenas o cardápio e vai para estado de escolha
            self.conversas[numero]["estado"] = ESTADOS["ESCOLHENDO_PRATO"]
            # Tentar buscar cardápio no Notion e complementar
            notion_text = self._buscar_notion_texto("cardapio") or self._buscar_notion_texto("cardápio")
            if notion_text:
                return "🍽️ Cardápio (Notion):\n\n" + notion_text[:800] + "\n\n" + self._mostrar_cardapio()
            return self._mostrar_cardapio()

        elif mensagem in ["2", "promocoes", "promoções"]:
            # Opção 2: Mostra promoções depois mostra cardápio
            notion_text = self._buscar_notion_texto("promoções") or self._buscar_notion_texto("promocoes")
            if notion_text:
                promo_msg = "📢 Promoções (Notion):\n\n" + notion_text[:800] + "\n\n"
            else:
                promo_msg = "📢 Promoções da semana:\n- Compre 5, leve 6!\n\n"
            
            # Mostra promoções e depois vai para cardápio
            self.conversas[numero]["estado"] = ESTADOS["ESCOLHENDO_PRATO"]
            return promo_msg + self._mostrar_cardapio()

        elif mensagem in ["3", "ja sei", "já sei"]:
            # Opção 3: Pula direto para escolha de prato (mostra cardápio com preços)
            self.conversas[numero]["estado"] = ESTADOS["ESCOLHENDO_PRATO"]
            return "Ótimo! Aqui está nosso cardápio:\n\n" + self._mostrar_cardapio()

        elif mensagem in ["4", "informacoes", "informações", "info"]:
            # Opção 4: Mostra informações com opção de ver cardápio
            notion_text = (
                self._buscar_notion_texto("informações")
                or self._buscar_notion_texto("informacoes")
            )
            if notion_text:
                info_msg = "📍 Informações (Notion):\n\n" + notion_text[:800] + "\n\n"
            else:
                info_msg = (
                    "📍 Informações:\n"
                    "- Entrega: 40-50 min\n"
                    "- Taxa: R$ 5,00\n"
                    "- Funcionamento: 11h-15h / 18h-22h\n\n"
                )
            # Após mostrar informações, continua no menu principal e oferece opções
            self.conversas[numero]["estado"] = ESTADOS["MENU_PRINCIPAL"]
            return info_msg + "Quer ver o cardápio? Digite 1 para ver o cardápio.\nOu 2 para Promoções."

        else:
            return (
                "Não entendi. Escolha uma opção:\n"
                "[1] Ver cardápio\n"
                "[2] Promoções\n"
                "[3] Já sei o que quero\n"
                "[4] Informações"
            )

    def _mostrar_cardapio(self) -> str:
        """Mostra cardápio"""
        texto = "🍽️ *Cardápio:*\n\n"
        for num, prato in CARDAPIO.items():
            preco_reais = prato["preco"] / 100
            texto += f"[{num}] {prato['nome']} - R$ {preco_reais:.2f}\n"
        texto += "\n_Digite o número do prato que deseja_"
        return texto

    def _escolher_prato(self, numero: str, mensagem: str) -> str:
        """Cliente escolhe prato - Vai direto para pedir endereço"""
        # Extrair número do prato (1-4)
        match = re.search(r'[1-4]', mensagem)
        if not match:
            return "Escolha um número de 1 a 4:\n\n" + self._mostrar_cardapio()

        num_prato = match.group()

        if num_prato not in CARDAPIO:
            return "Número inválido! Escolha de 1 a 4:\n\n" + self._mostrar_cardapio()

        # Salvar escolha
        self.conversas[numero]["prato"] = CARDAPIO[num_prato]
        
        # Vai direto para pedir endereço (sem confirmação)
        self.conversas[numero]["estado"] = ESTADOS["PEDINDO_ENDERECO"]

        prato = CARDAPIO[num_prato]
        preco = prato["preco"] / 100
        return (
            f"Perfeito! ✅\n\n"
            f"*{prato['nome']}* - R$ {preco:.2f}\n\n"
            f"Qual o endereço de entrega?\n"
            f"_(Rua, número, bairro)_"
        )

    def _confirmar_pedido(self, numero: str, mensagem: str) -> str:
        """Confirmação do pedido"""
        if mensagem in ["1", "sim", "s", "confirmo", "ok"]:
            self.conversas[numero]["estado"] = ESTADOS["PEDINDO_ENDERECO"]
            return (
                "Perfeito! ✅\n\n"
                "Qual o endereço de entrega?\n"
                "_(Rua, número, bairro)_"
            )

        elif mensagem in ["2", "nao", "não", "n", "cancelar"]:
            self.conversas[numero]["estado"] = ESTADOS["ESCOLHENDO_PRATO"]
            self.conversas[numero]["prato"] = None
            return "Sem problemas! Vamos escolher outro:\n\n" + self._mostrar_cardapio()

        else:
            return (
                "Digite:\n"
                "[1] para confirmar\n"
                "[2] para escolher outro prato"
            )

    def _pedir_endereco(self, numero: str, mensagem: str) -> str:
        """Pede endereço"""
        if len(mensagem) < 10:
            return "Por favor, me passe o endereço completo (rua, número, bairro)"

        self.conversas[numero]["endereco"] = mensagem
        self.conversas[numero]["estado"] = ESTADOS["PEDINDO_PAGAMENTO"]

        return (
            "Endereço anotado! 📍\n\n"
            "Como você quer pagar?\n"
            "[1] PIX\n"
            "[2] Dinheiro na entrega"
        )

    def _pedir_pagamento(self, numero: str, mensagem: str) -> str:
        """Forma de pagamento"""
        if mensagem in ["1", "pix"]:
            self.conversas[numero]["pagamento"] = "pix"
            self.conversas[numero]["estado"] = ESTADOS["PEDINDO_CPF"]
            return (
                "Ótimo! Vou gerar o PIX pra você. 💰\n\n"
                "Quer CPF na nota?\n"
                "Digite o CPF ou 'não'"
            )

        elif mensagem in ["2", "dinheiro"]:
            self.conversas[numero]["pagamento"] = "dinheiro"
            self.conversas[numero]["estado"] = ESTADOS["TROCO"]
            return (
                "Beleza! Pagamento em dinheiro. 💵\n\n"
                "Precisa de troco?\n"
                "[1] Sim\n"
                "[2] Não"
            )

        else:
            return (
                "Escolha a forma de pagamento:\n"
                "[1] PIX\n"
                "[2] Dinheiro"
            )

    def _pedir_cpf(self, numero: str, mensagem: str) -> str:
        """Pede CPF (opcional)"""
        # Extrair CPF se fornecido
        cpf = re.sub(r'[^0-9]', '', mensagem)

        if mensagem in ["nao", "não", "n", "sem cpf", "nenhum"]:
            cpf = ""
        elif cpf and len(cpf) == 11 and cpf_valido(cpf):
            self.conversas[numero]["cpf"] = cpf
        else:
            cpf = ""

        # Gerar PIX aqui
        self.conversas[numero]["estado"] = ESTADOS["FINALIZADO"]

        # Sinalizar que precisa gerar PIX
        return f"GERAR_PIX:{numero}"

    def _troco(self, numero: str, mensagem: str) -> str:
        """Troco"""
        if mensagem in ["1", "sim", "s"]:
            return (
                "Quanto você vai pagar?\n"
                "_(Digite o valor)_"
            )
        elif mensagem in ["2", "nao", "não", "n"]:
            self.conversas[numero]["estado"] = ESTADOS["FINALIZADO"]
            return self._finalizar_dinheiro(numero)

        # Se é um valor
        if any(c.isdigit() for c in mensagem):
            self.conversas[numero]["troco"] = mensagem
            self.conversas[numero]["estado"] = ESTADOS["FINALIZADO"]
            return self._finalizar_dinheiro(numero)

        return "Digite [1] para sim ou [2] para não"

    def _finalizar_dinheiro(self, numero: str) -> str:
        """Finaliza pedido em dinheiro"""
        prato = self.conversas[numero]["prato"]
        return (
            "✅ *Pedido confirmado!*\n\n"
            f"📦 {prato['nome']}\n"
            f"💵 R$ {prato['preco']/100:.2f}\n"
            f"💰 Pagamento: Dinheiro\n\n"
            "🛵 Tempo de entrega: 40-50 minutos\n"
            "O motoboy levará o troco! 😊"
        )

    def obter_dados_pix(self, numero: str) -> Optional[Dict]:
        """Retorna dados para gerar PIX"""
        if numero not in self.conversas:
            return None

        conv = self.conversas[numero]
        if not conv.get("prato"):
            return None

        return {
            "produto": conv["prato"]["nome"],
            "valor_centavos": conv["prato"]["preco"],
            "cliente_nome": "Cliente",  # Pode extrair do WhatsApp
            "cliente_telefone": numero,
            "cliente_cpf": conv.get("cpf", ""),
        }

    def resetar_conversa(self, numero: str):
        """Reseta conversa do cliente"""
        if numero in self.conversas:
            del self.conversas[numero]

    def _buscar_notion_texto(self, query: str) -> Optional[str]:
        """Busca uma página no Notion e retorna texto concatenado dos blocos.
        Requer NOTION_API_KEY e pacote notion-client instalados.
        """
        if not Client or not NOTION_API_KEY:
            return None
        try:
            client = Client(auth=NOTION_API_KEY)
            resp = client.search(query=query, filter={"property": "object", "value": "page"})
            results = resp.get("results", [])
            if not results:
                return None
            page_id = results[0].get("id")
            blocks = client.blocks.children.list(block_id=page_id)
            lines = []
            for block in blocks.get("results", []):
                btype = block.get("type")
                content = block.get(btype, {})
                rich = content.get("rich_text") or content.get("rich_text", [])
                if btype.startswith("heading_"):
                    text = "".join([t.get("plain_text", "") for t in content.get("rich_text", [])])
                    if text.strip():
                        lines.append(f"**{text.strip()}**")
                elif btype == "paragraph":
                    text = "".join([t.get("plain_text", "") for t in rich])
                    if text.strip():
                        lines.append(text.strip())
            texto = "\n".join(lines).strip()
            return texto or None
        except Exception:
            return None

    def gerar_pix(self, numero: str) -> str:
        """Gera PIX via AbacatePay e retorna mensagem amigável com o código.
        - Usa a variável de ambiente 'AbacatePay_API_Key' (ou 'ABACATEPAY_API_KEY').
        - Inclui CPF (taxId) apenas se for válido para evitar erro 'Invalid taxId'.
        """
        print(f"🔧 gerar_pix() chamado para número: {numero}")

        dados = self.obter_dados_pix(numero)
        if not dados:
            print(f"❌ Dados do pedido não encontrados para {numero}")
            return "❌ Não encontrei dados do pedido para gerar PIX. Volte ao menu e escolha um prato."

        print(f"✅ Dados do pedido obtidos: {dados}")

        api_key = (
            os.getenv("AbacatePay_API_Key")
            or os.getenv("ABACATEPAY_API_KEY")
        )
        if not api_key:
            print("❌ API Key não encontrada")
            return "❌ AbacatePay_API_Key não configurada no .env. Configure e tente novamente."

        print(f"✅ API Key encontrada: {api_key[:10]}...")

        descricao = f"Marmiratria - {dados['produto']}"
        valor_centavos = int(dados["valor_centavos"])
        cliente_nome = dados["cliente_nome"]
        cliente_telefone = dados["cliente_telefone"]
        cliente_cpf = re.sub(r"[^0-9]", "", dados.get("cliente_cpf", "") or "")

        # Monta payload básico
        payload = {
            "amount": valor_centavos,
            "expiresIn": 3600,  # 1 hora
            "description": descricao,
            "customer": {
                "name": cliente_nome,
                "cellphone": cliente_telefone,
                "email": "cliente@email.com",
            },
            "metadata": {
                "produto": dados["produto"],
                "valor_reais": float(valor_centavos) / 100.0,
            },
        }

        # Sempre incluir taxId
        cpf_para_envio = cliente_cpf if cpf_valido(cliente_cpf) else gerar_cpf_valido()
        payload["customer"]["taxId"] = cpf_para_envio

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        print(f"📤 Enviando requisição para AbacatePay...")
        print(f"📦 Payload: {payload}")

        try:
            resp = requests.post(
                "https://api.abacatepay.com/v1/pixQrCode/create",
                json=payload,
                headers=headers,
                timeout=15,
            )
            print(f"📥 Resposta recebida: Status {resp.status_code}")

            if resp.status_code in (200, 201):
                response_data = resp.json()
                print(f"📊 Resposta JSON completa: {response_data}")

                # A resposta pode vir diretamente ou dentro de 'data'
                data = response_data.get("data", response_data)

                # Extrair campos da resposta da AbacatePay
                # brCode = PIX copia e cola (texto)
                # brCodeBase64 = QR Code em base64 (data URI)
                pix_code = data.get("brCode") or data.get("qrCode") or data.get("pix_code")
                qr_base64 = data.get("brCodeBase64") or data.get("qrCodeUrl") or data.get("qr_code_url")

                valor_reais = float(valor_centavos) / 100.0

                # Debug: verificar dados recebidos
                print(f"🔍 Debug PIX - QR Base64: {qr_base64[:80] if qr_base64 else 'None'}...")
                print(f"🔍 Debug PIX - Code: {pix_code[:50] if pix_code else 'None'}...")

                # Mensagem 1: Informações do PIX
                texto_info = (
                    "✅ *PIX gerado com sucesso!*\n\n"
                    f"📦 {dados['produto']}\n"
                    f"💰 Valor: R$ {valor_reais:.2f}\n\n"
                    "🔢 *Copia e Cola e QR Code:*"
                )

                # Salvar dados para enviar mensagens 2 e 3 separadamente
                self.conversas[numero]["qr_base64"] = qr_base64
                self.conversas[numero]["pix_code"] = pix_code
                self.conversas[numero]["enviar_pix"] = True

                print(f"✅ Dados salvos na conversa. enviar_pix={self.conversas[numero].get('enviar_pix')}")
                print(f"✅ PIX Code length: {len(pix_code) if pix_code else 0}")
                print(f"✅ QR Base64 length: {len(qr_base64) if qr_base64 else 0}")

                return texto_info
            else:
                # Tentar mostrar erro amigável
                try:
                    err = resp.json()
                    msg = err.get("error") or err.get("message") or str(err)
                except Exception:
                    msg = resp.text
                return f"❌ Erro ao criar PIX ({resp.status_code}): {msg}"
        except Exception as e:
            return f"❌ Erro de comunicação com AbacatePay: {e}"


def cpf_valido(cpf: str) -> bool:
    """Valida CPF (11 dígitos) com cálculo dos dígitos verificadores."""
    cpf = re.sub(r"[^0-9]", "", cpf or "")
    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False

    # Primeiro dígito
    s1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = (s1 * 10) % 11
    if d1 == 10:
        d1 = 0
    if d1 != int(cpf[9]):
        return False

    # Segundo dígito
    s2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = (s2 * 10) % 11
    if d2 == 10:
        d2 = 0
    return d2 == int(cpf[10])

def gerar_cpf_valido() -> str:
    base = [random.randint(0, 9) for _ in range(9)]
    if len(set(base)) == 1:
        base[0] = (base[0] + 1) % 10
    s1 = sum(base[i] * (10 - i) for i in range(9))
    d1 = (s1 * 10) % 11
    if d1 == 10:
        d1 = 0
    s2 = sum((base + [d1])[i] * (11 - i) for i in range(10))
    d2 = (s2 * 10) % 11
    if d2 == 10:
        d2 = 0
    return ''.join(str(x) for x in (base + [d1, d2]))

# Instância global
bot_simples = BotSimples()
