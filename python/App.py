from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import sys
from bot_simples import bot_simples

# Agente IA desativado. Usando bot_simples para todas as respostas.

load_dotenv()

app = Flask(__name__)

# Garantir que respostas JSON mantenham Unicode e evitar erros de encoding
app.config['JSON_AS_ASCII'] = False

# Forçar saída UTF-8 segura no Windows para evitar UnicodeEncodeError ao imprimir emojis
try:
    # Python 3.7+ suporta reconfigure
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    # Fallback: definir variável de ambiente para I/O UTF-8
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# Configurações
EVOLUTION_API = os.getenv("EVOLUTION_API_URL")
INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME")
API_KEY = os.getenv("API_KEY_EVOLUTION")

# Cache simples de endpoints que retornaram 404 previamente
EVOLUTION_DISABLED_ENDPOINTS: set[str] = set()
# Cache de números inválidos (não estão no WhatsApp ou bloqueados pelo servidor)
EVOLUTION_INVALID_NUMBERS: set[str] = set()

def _normalize_number(number: str | None) -> str | None:
    """Normaliza número para formato E.164 sem sufixos de JID.
    - Remove qualquer sufixo após '@' (incluindo @lid, @s.whatsapp.net, @c.us)
    - Remove espaços e caracteres não numéricos
    - Mantém apenas dígitos (sem '+')
    - Para @lid: extrai apenas os dígitos antes do @
    """
    if not number:
        return None
    s = str(number).strip()

    # Remover QUALQUER sufixo JID (incluindo @lid)
    if '@' in s:
        s = s.split('@', 1)[0]

    import re
    s = ''.join(re.findall(r'\d+', s))

    # Validar se é um número de telefone válido (pelo menos 10 dígitos)
    if len(s) < 10:
        return None

    return s or None


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "running"}), 200

@app.route('/evolution-health', methods=['GET'])
def evolution_health():
    """Diagnóstico básico da Evolution API e instância."""
    if not (EVOLUTION_API and INSTANCE_NAME and API_KEY):
        return jsonify({
            "ok": False,
            "error": "EVOLUTION_API_URL/INSTANCE_NAME/API_KEY_EVOLUTION ausentes",
            "env": {
                "EVOLUTION_API_URL": bool(EVOLUTION_API),
                "EVOLUTION_INSTANCE_NAME": bool(INSTANCE_NAME),
                "API_KEY_EVOLUTION": bool(API_KEY)
            }
        }), 500
    headers = {"apikey": API_KEY, "Authorization": f"Bearer {API_KEY}"}
    endpoints = [
        ("GET", f"{EVOLUTION_API}/health"),
        ("GET", f"{EVOLUTION_API}/instances/{INSTANCE_NAME}/status"),
        ("GET", f"{EVOLUTION_API}/instance/info/{INSTANCE_NAME}"),
    ]
    results = []
    for method, url in endpoints:
        try:
            resp = requests.request(method, url, headers=headers, timeout=8)
            results.append({
                "url": url,
                "code": resp.status_code,
                "body": (resp.text or "")[:400]
            })
        except Exception as e:
            results.append({
                "url": url,
                "error": str(e)
            })
    return jsonify({"ok": True, "checks": results}), 200


@app.route('/notion-health', methods=['GET'])
def notion_health():
    """Teste de conexão com a API do Notion.
    - GET /notion-health            -> testa busca genérica (search)
    - GET /notion-health?page_id=ID -> testa leitura de blocos da página
    """
    try:
        api_key = os.getenv("NOTION_API_KEY") or os.getenv("Notion_API_Key")
        if not api_key:
            return jsonify({"ok": False, "error": "Missing NOTION_API_KEY"}), 500
        from notion_client import Client
        client = Client(auth=api_key)

        page_id = (request.args.get('page_id') or '').strip()
        query = (request.args.get('query') or '').strip()

        if page_id:
            try:
                resp = client.blocks.children.list(block_id=page_id)
                count = len(resp.get('results', []) or [])
                return jsonify({
                    "ok": True,
                    "mode": "blocks.children.list",
                    "count": count
                }), 200
            except Exception as e:
                return jsonify({
                    "ok": False,
                    "mode": "blocks.children.list",
                    "error": str(e)
                }), 200
        else:
            try:
                resp = client.search(query=query)
                results = resp.get('results', []) or []
                sample = None
                if results:
                    r0 = results[0]
                    sample = {
                        "id": r0.get('id'),
                        "object": r0.get('object')
                    }
                return jsonify({
                    "ok": True,
                    "mode": "search",
                    "count": len(results),
                    "sample": sample
                }), 200
            except Exception as e:
                return jsonify({
                    "ok": False,
                    "mode": "search",
                    "error": str(e)
                }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 200


@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint genérico para receber eventos Evolution diretamente."""
    try:
        payload = request.get_json(force=True, silent=True) or {}
        return handle_evolution_event(payload, source_path='webhook')
    except Exception as e:
        print(f"❌ Erro no /webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 200


@app.route('/process-event', methods=['POST'])
def process_event():
    """Endpoint para receber eventos encaminhados pelo webhook.py."""
    try:
        payload = request.get_json(force=True, silent=True) or {}
        return handle_evolution_event(payload, source_path='process-event')
    except Exception as e:
        print(f"❌ Erro no /process-event: {e}")
        return jsonify({"status": "error", "message": str(e)}), 200


@app.route('/bot-simples', methods=['POST'])
def bot_simples_route():
    """Usa o bot simples (fluxo por estados) e gera PIX quando apropriado."""
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception as e:
        print(f"❌ Erro ao ler JSON no /bot-simples: {e}")
        return jsonify({"status": "error", "message": str(e)}), 200

    event_type = (payload or {}).get('event')
    data = (payload or {}).get('data', payload or {})
    items = _iter_event_items(event_type, data)

    processed = False
    last_reply = None
    last_number = None

    for entry in items:
        text, number = extract_text_and_number(event_type, entry)
        if text and number:
            processed = True
            try:
                from bot_simples import bot_simples
                reply = bot_simples.processar_mensagem_com_pix(number, text)
                print(f"🤖[bot_simples] Número: {number} | Texto: {text} | Resposta: {reply[:150]}")

                # Mensagem 1: Informações do PIX
                send_text_web(number, reply)

                # Se PIX foi gerado, enviar mensagens 2 e 3
                if number in bot_simples.conversas:
                    conv = bot_simples.conversas[number]
                    print(f"🔍 Debug - Conversa keys: {list(conv.keys())}")
                    print(f"🔍 Debug - enviar_pix: {conv.get('enviar_pix')}")

                    if conv.get("enviar_pix"):
                        pix_code = conv.get("pix_code")
                        qr_base64 = conv.get("qr_base64")

                        print(f"🔍 Debug - pix_code existe: {bool(pix_code)}")
                        print(f"🔍 Debug - qr_base64 existe: {bool(qr_base64)}")

                        # Mensagem 2: Código PIX copia e cola (sem formatação)
                        if pix_code:
                            print(f"📋 Enviando código PIX copia e cola ({len(pix_code)} chars)")
                            send_text_web(number, pix_code)
                        else:
                            print("⚠️ pix_code está vazio ou None")

                        # Mensagem 3: Imagem do QR Code (base64)
                        if qr_base64:
                            print(f"📸 Enviando QR Code como imagem (base64): {qr_base64[:80]}...")
                            valor = conv.get("prato", {}).get("preco", 0) / 100
                            ok_media = send_media_web(
                                number=number,
                                media_type="image",
                                file_name="qrcode_pix.png",
                                caption=f"Escaneie o QR Code para pagar R$ {valor:.2f}",
                                media=qr_base64
                            )
                            print(f"📸 Resultado envio mídia: {ok_media}")
                            if ok_media and not str(number).startswith('web-'):
                                conv.pop("qr_base64", None)
                                conv.pop("pix_code", None)
                                conv.pop("enviar_pix", None)
                        else:
                            print("⚠️ qr_base64 está vazio ou None")
                    else:
                        print("ℹ️ Flag enviar_pix não está ativa")

                last_reply = reply
                last_number = number
            except Exception as e:
                print(f"❌ Erro no bot_simples: {e}")
        else:
            print("ℹ️ /bot-simples: item sem texto/número processáveis.")
            print(f"📦 Dump: {_safe_dump(entry)}")

    # Incluir dados de PIX no retorno quando disponíveis (web)
    extra = {}
    try:
        from bot_simples import bot_simples as _bs
        if last_number and last_number in _bs.conversas:
            conv = _bs.conversas.get(last_number, {})
            if conv.get("enviar_pix"):
                pix_code = conv.get("pix_code")
                qr_base64 = conv.get("qr_base64")
                produto = conv.get("prato", {}).get("nome")
                valor_centavos = conv.get("prato", {}).get("preco")
                extra["pix_data"] = {
                    "pix_copia_cola": pix_code,
                    "qr_code_url": qr_base64,
                    "produto": produto,
                    "valor": (valor_centavos or 0) / 100.0
                }
    except Exception:
        pass

    return jsonify({
        "status": "success",
        "processed": processed,
        "reply": last_reply,
        "number": last_number,
        **extra
    }), 200


@app.route('/messages-upsert', methods=['POST'])
def messages_upsert():
    """Endpoint específico para eventos MESSAGES_UPSERT do Evolution API"""
    print("\n" + "=" * 60)
    print("🔔 MESSAGES-UPSERT ENDPOINT CHAMADO!")
    print("=" * 60)
    return process_event('/messages-upsert')


@app.route('/connection-update', methods=['POST'])
def connection_update():
    """Endpoint para CONNECTION_UPDATE"""
    print("\n⚠️ CONNECTION-UPDATE recebido (será ignorado)")
    return jsonify({"status": "ignored", "event": "connection.update"}), 200


@app.route('/<path:endpoint>', methods=['POST', 'GET'])
def dynamic_routes(endpoint: str):
    """Captura rotas como /messages-upsert, /chats-update, /contacts-update diretamente."""
    print(f"\n📥 Requisição recebida em: /{endpoint}")
    print(f"Método: {request.method}")

    try:
        payload = request.get_json(force=True, silent=True) or {}
        print(f"Payload keys: {list(payload.keys()) if payload else 'vazio'}")

        # Deriva o tipo de evento a partir do caminho
        event_map = {
            'messages-upsert': 'messages.upsert',
            'chats-update': 'chats.update',
            'contacts-update': 'contacts.update',
        }
        derived_event = event_map.get(endpoint.strip().lower(), endpoint)
        # Injeta event se não existir
        if 'event' not in payload:
            payload['event'] = derived_event
        return handle_evolution_event(payload, source_path=endpoint)
    except Exception as e:
        print(f"❌ Erro em /{endpoint}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 200

def handle_evolution_event(payload: dict | list, source_path: str = ''):
    """
    Normaliza e processa eventos da Evolution API.
    - Suporta: message, messages.upsert, chats.update, contacts.update
    - Extrai texto e número do remetente para responder via Agente e enviar pelo Evolution.
    """
    if isinstance(payload, list):
        for item in payload:
            handle_evolution_event(item, source_path)
        return

    event_type = (payload or {}).get('event')
    data = (payload or {}).get('data', payload or {})

    print("\n" + "=" * 60)
    print(f"📡 Fonte: {source_path} | 🎯 Evento: {event_type}")
    print("=" * 60)

    # Ignorar eventos que não contêm mensagens processáveis
    EVENTOS_IGNORA = ['contacts.update', 'chats.update', 'connection.update', 'qr.updated']
    if event_type in EVENTOS_IGNORA:
        print(f"ℹ️ Evento {event_type} ignorado (não contém mensagens processáveis)")
        return jsonify({"status": "ignored", "event": event_type}), 200

    # Normalizar itens de evento (suporta listas e formatos Baileys com data.messages)
    items = _iter_event_items(event_type, data)
    processed = False
    last_reply = None
    last_number = None
    for entry in items:
        # Processar somente quando houver texto e número claro
        text, number = extract_text_and_number(event_type, entry)

        if text and number:
            processed = True
            print(f"💬 Texto: {text}")
            print(f"👤 Número: {number}")
            try:
                reply = bot_simples.processar_mensagem_com_pix(number, text)
                print(f"🤖 Resposta (bot_simples): {reply}")

                # Mensagem 1: Informações do PIX
                send_text(number, reply)

                # Se PIX foi gerado, enviar mensagens 2 e 3
                if number in bot_simples.conversas:
                    conv = bot_simples.conversas[number]
                    print(f"🔍 Debug - Conversa keys: {list(conv.keys())}")
                    print(f"🔍 Debug - enviar_pix: {conv.get('enviar_pix')}")

                    if conv.get("enviar_pix"):
                        pix_code = conv.get("pix_code")
                        qr_base64 = conv.get("qr_base64")

                        print(f"🔍 Debug - pix_code existe: {bool(pix_code)}")
                        print(f"🔍 Debug - qr_base64 existe: {bool(qr_base64)}")

                        # Mensagem 2: Código PIX copia e cola (sem formatação)
                        if pix_code:
                            print(f"📋 Enviando código PIX copia e cola ({len(pix_code)} chars)")
                            send_text(number, pix_code)
                        else:
                            print("⚠️ pix_code está vazio ou None")

                        # Mensagem 3: Imagem do QR Code (base64)
                        if qr_base64:
                            print(f"📸 Enviando QR Code como imagem (base64): {qr_base64[:80]}...")
                            valor = conv.get("prato", {}).get("preco", 0) / 100
                            ok_media = send_media(
                                number=number,
                                media_type="image",
                                file_name="qrcode_pix.png",
                                caption=f"Escaneie o QR Code para pagar R$ {valor:.2f}",
                                media=qr_base64
                            )
                            print(f"📸 Resultado envio mídia: {ok_media}")
                            if ok_media:
                                # Limpar dados do QR após envio bem-sucedido
                                conv.pop("qr_base64", None)
                                conv.pop("pix_code", None)
                                conv.pop("enviar_pix", None)
                        else:
                            print("⚠️ qr_base64 está vazio ou None")
                    else:
                        print("ℹ️ Flag enviar_pix não está ativa")

                last_reply = reply
                last_number = number
            except Exception as e:
                print(f"❌ Erro ao gerar/enviar resposta: {e}")
        else:
            try:
                print(f"ℹ️ Item sem texto/número para resposta. Registrado. Keys: {list((entry or {}).keys())}")
                print(f"📦 Dump: {_safe_dump(entry)}")
            except Exception:
                print("ℹ️ Item sem texto/número para resposta. (dump indisponível)")

    if not processed:
        print("ℹ️ Evento sem itens processáveis.")

    return jsonify({
        "status": "success",
        "processed": processed,
        "reply": last_reply,
        "number": last_number
    }), 200


def extract_text_and_number(event_type: str | None, item: dict):
    """Extrai texto e número do payload conforme o tipo de evento, cobrindo variações comuns da Evolution/Baileys."""
    if not item:
        return None, None

    # Helpers de leitura
    def clean_number(n: str | None):
        if not n:
            return None
        n = n.strip()
        if '@' in n:
            n = n.split('@', 1)[0]
        return n

    def text_from_message(msg: dict):
        # Conversas/Texto estendido
        if 'conversation' in msg:
            return msg.get('conversation')
        etm = msg.get('extendedTextMessage') or {}
        if isinstance(etm, dict) and etm.get('text'):
            return etm.get('text')
        # Botões/Listas
        brm = msg.get('buttonsResponseMessage') or {}
        if isinstance(brm, dict):
            return brm.get('selectedDisplayText') or brm.get('selectedButtonId')
        lrm = msg.get('listResponseMessage') or {}
        if isinstance(lrm, dict):
            single = lrm.get('singleSelectReply') or {}
            return single.get('selectedRowId') or single.get('title')
        # Imagem/Vídeo com legenda
        im = msg.get('imageMessage') or {}
        if isinstance(im, dict) and im.get('caption'):
            return im.get('caption')
        vm = msg.get('videoMessage') or {}
        if isinstance(vm, dict) and vm.get('caption'):
            return vm.get('caption')
        # Documento
        dm = msg.get('documentMessage') or {}
        if isinstance(dm, dict):
            return dm.get('caption') or '[DOCUMENT_MESSAGE]'
        # Áudio/ptt
        if msg.get('audioMessage') or msg.get('ptt') or msg.get('voiceMessage'):
            return '[AUDIO_MESSAGE]'
        return None

    # Evento simples: message (Evolution)
    if event_type == 'message' or item.get('type') == 'message':
        text = item.get('body') or item.get('text') or None
        # Capturar legendas em mídia
        if not text:
            if (item.get('type') in ['image', 'video', 'document']) and isinstance(item.get('media'), dict):
                text = item.get('media', {}).get('caption')
            if item.get('type') == 'audio':
                text = '[AUDIO_MESSAGE]'
        number = clean_number(item.get('from') or item.get('jid') or item.get('chatId'))
        return (text or None), (number or None)

    # Evento Baileys: messages.upsert (Evolution v3/v4)
    if event_type == 'messages.upsert':
        key = item.get('key') or {}
        message = item.get('message') or {}
        from_me = bool(key.get('fromMe', False))
        if from_me:
            return None, None
        number = clean_number(key.get('remoteJid') or item.get('from') or item.get('jid') or item.get('chatId'))
        text = text_from_message(message)
        return (text or None), (number or None)

    # Fallback: tentar campos genéricos
    text = item.get('body') or item.get('text')
    number = clean_number(item.get('from') or item.get('jid') or item.get('chatId'))
    return (text or None), (number or None)

def _iter_event_items(event_type: str | None, data: dict | list):
    """Normaliza os itens do evento em uma lista processável."""
    if event_type == 'messages.upsert':
        # Formatos possíveis: data é um dict com 'messages' (lista) ou um item único
        if isinstance(data, dict) and isinstance(data.get('messages'), list):
            return data.get('messages')
        if isinstance(data, list):
            return data
        return [data]
    # Demais eventos: aceitar lista ou item único
    if isinstance(data, list):
        return data
    return [data]

def _safe_dump(obj: dict, maxlen: int = 600):
    try:
        import json
        s = json.dumps(obj or {}, ensure_ascii=False)
        return s if len(s) <= maxlen else (s[:maxlen] + '…')
    except Exception:
        return str(obj)[:maxlen]

# Função de geração via agente IA removida

def send_text_web(number: str, text: str):
    """Wrapper para enviar texto, detectando usuários web."""
    # Para usuários web, apenas logar e retornar (não enviar para WhatsApp)
    if number.startswith('web-'):
        print(f"🌐 Usuário web detectado: {number} - mensagem: {text[:50]}...")
        return
    # Para números normais, usar função original
    return send_text_original(number, text)

def send_media_web(number: str, media_type: str, file_name: str, caption: str, media: str):
    """Wrapper para enviar mídia, detectando usuários web."""
    # Para usuários web, apenas logar e retornar (não enviar para WhatsApp)
    if number.startswith('web-'):
        print(f"🌐 Usuário web detectado: {number} - envio de mídia ignorado")
        return True  # Retornar sucesso para não quebrar o fluxo
    # Para números normais, usar função original
    return send_media_original(number, media_type, file_name, caption, media)

def send_media_original(number: str, media_type: str, file_name: str, caption: str, media: str):
    """Envia mídia via Evolution API."""
    if not (EVOLUTION_API and INSTANCE_NAME and API_KEY):
        print("❌ Configuração ausente: verifique EVOLUTION_API_URL, EVOLUTION_INSTANCE_NAME, API_KEY_EVOLUTION no .env")
        return
    number_norm = _normalize_number(number)
    if not number_norm:
        print(f"❌ Número inválido para envio de texto: {number}")
        return
    if number_norm in EVOLUTION_INVALID_NUMBERS:
        print(f"⛔ Ignorando envio: número não está no WhatsApp (cache) -> {number_norm}")
        return

    # Usar apenas um endpoint canônico e um formato de payload estável
    endpoints = [
        f"{EVOLUTION_API}/message/sendText/{INSTANCE_NAME}",
    ]
    # Payload compatível com versões atuais da Evolution API
    def build_payloads(url: str):
        return [{"number": number_norm, "textMessage": {"text": text}}]
    headers = {"Content-Type": "application/json", "apikey": API_KEY}
    # Alguns servidores usam Authorization Bearer
    headers["Authorization"] = f"Bearer {API_KEY}"

    last_error = None
    for url in endpoints:
        if url in EVOLUTION_DISABLED_ENDPOINTS:
            print(f"⛔ Ignorando endpoint desativado (404 prévio): {url}")
            continue
        try:
            payload = build_payloads(url)[0]
            print(f"➡️ Enviando texto via {url} para {number_norm}")
            resp = requests.post(url, json=payload, headers=headers, timeout=12)
            if resp.status_code < 300:
                print(f"✅ Texto enviado para {number_norm}: {resp.status_code} via {url}")
                return
            else:
                # Log compacto para reduzir ruído em 400
                snippet = resp.text[:200]
                print(f"⚠️ Falha ({resp.status_code}) em {url}: {snippet}")
                if resp.status_code == 404:
                    EVOLUTION_DISABLED_ENDPOINTS.add(url)
                # Se o servidor indicar que o número/jid não existe, cachear para evitar novas tentativas
                if resp.status_code == 400:
                    try:
                        data = resp.json()
                        msg_list = ((data or {}).get('response') or {}).get('message') or []
                        for item in msg_list:
                            if isinstance(item, dict) and item.get('exists') is False:
                                bad_num = item.get('number') or number_norm
                                EVOLUTION_INVALID_NUMBERS.add(str(bad_num))
                                print(f"🚫 Número inválido detectado pelo Evolution (exists=false): {bad_num}")
                                break
                    except Exception:
                        pass
        except Exception as e:
            last_error = e
            print(f"⚠️ Erro ao enviar texto via {url}: {e}")

    if last_error:
        print(f"❌ Falha ao enviar resposta após tentativas: {last_error}")

def send_media(number: str, media_type: str, file_name: str, caption: str, media: str):
    """Envia mídia via Evolution API."""
    if not (EVOLUTION_API and INSTANCE_NAME and API_KEY):
        print("❌ Configuração ausente")
        return False

    number_norm = _normalize_number(number)
    if not number_norm:
        print(f"❌ Número inválido: {number}")
        return False

    if number_norm in EVOLUTION_INVALID_NUMBERS:
        print(f"⛔ Número não está no WhatsApp: {number_norm}")
        return False

    # Se for data URI, extrair apenas o base64
    media_clean = media
    if isinstance(media, str) and media.startswith("data:"):
        try:
            # data:image/png;base64,iVBORw0KG... -> iVBORw0KG...
            _, base64_data = media.split(",", 1)
            media_clean = base64_data
            print(f"📸 Data URI detectado, extraindo base64 puro")
        except Exception:
            pass

    # Endpoint principal
    url = f"{EVOLUTION_API}/message/sendMedia/{INSTANCE_NAME}"

    # Payload
    payload = {
        "number": number_norm,
        "mediaMessage": {
            "mediatype": media_type,
            "caption": caption,
            "fileName": file_name,
            "media": media_clean
        }
    }

    headers = {
        "Content-Type": "application/json",
        "apikey": API_KEY,
        "Authorization": f"Bearer {API_KEY}"
    }

    print(f"➡️ Enviando mídia para {number_norm}")
    print(f"📦 Media length: {len(media_clean) if media_clean else 0}")

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        if resp.status_code < 300:
            print(f"✅ Mídia enviada: {resp.status_code}")
            return True
        else:
            print(f"⚠️ Falha ({resp.status_code}): {resp.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


@app.route('/enviar-pix-whatsapp', methods=['POST'])
def enviar_pix_whatsapp():
    """
    Endpoint interno para enviar PIX já gerado via WhatsApp
    Body: {
        "numero_whatsapp": "5511999999999",
        "pix_data": {...}  # Dados retornados pelo checkout.js
    }
    """
    try:
        data = request.get_json()
        numero_whatsapp = data.get('numero_whatsapp')
        pix_data = data.get('pix_data', {})

        if not numero_whatsapp or not pix_data.get('success'):
            return jsonify({"error": "Dados inválidos"}), 400

        qr_code_url = pix_data.get('qr_code_url')
        pix_code = pix_data.get('pix_copia_cola')
        valor = pix_data.get('valor', 0)
        produto = pix_data.get('produto', 'Produto')

        # Mensagem 1: PIX copia e cola
        msg_copia_cola = (
            f"💰 *PIX Gerado!*\n\n"
            f"📦 Produto: {produto}\n"
            f"💵 Valor: R$ {valor:.2f}\n\n"
            f"*PIX Copia e Cola:*\n`{pix_code}`"
        )
        send_text(numero_whatsapp, msg_copia_cola)

        # Mensagem 2: QR Code
        ok_media = send_media(
            number=numero_whatsapp,
            media_type="image",
            file_name="qrcode_pix.png",
            caption=f"🔳 Escaneie para pagar R$ {valor:.2f}",
            media=qr_code_url
        )
        if not ok_media:
            ok_media_doc = send_media(
                number=numero_whatsapp,
                media_type="document",
                file_name="qrcode_pix.png",
                caption=f"🔳 Escaneie para pagar R$ {valor:.2f}",
                media=qr_code_url
            )
            ok_media = ok_media or ok_media_doc

        # Mensagem 3: validade (padrão 5 minutos)
        expiracao_info = pix_data.get('expires_at') or ''
        msg_validade = (
            f"⏳ Validade: 5 minutos (300 segundos)."
            + (f"\nAté: {expiracao_info}" if expiracao_info else "")
        )
        send_text(numero_whatsapp, msg_validade)

        return jsonify({
            "success": True,
            "message": "PIX enviado via WhatsApp"
        }), 200

    except Exception as e:
        print(f"❌ Erro ao enviar PIX via WhatsApp: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/gerar-pix', methods=['POST'])
def gerar_pix():
    """
    Endpoint para gerar PIX e enviar QR Code
    Body: {
        "produto": "Baião de Dois",
        "valor_centavos": 2890,
        "cliente_nome": "João",
        "cliente_telefone": "5511999999999",
        "numero_whatsapp": "5511999999999"
    }
    """
    try:
        data = request.get_json()
        produto = data.get('produto', 'Produto')
        valor_centavos = data.get('valor_centavos', 0)
        cliente_nome = data.get('cliente_nome', 'Cliente')
        cliente_telefone = data.get('cliente_telefone', '')
        cliente_cpf = data.get('cliente_cpf', '')
        numero_whatsapp = data.get('numero_whatsapp')
        validade_segundos = int(data.get('validade_segundos') or 300)  # padrão: 5 minutos (300 s)

        if not numero_whatsapp or not valor_centavos:
            return jsonify({"error": "numero_whatsapp e valor_centavos são obrigatórios"}), 400

        # Chamar checkout.js via subprocess
        import subprocess
        import json as json_lib

        script_path = os.path.join(os.path.dirname(__file__), 'checkout_cli.js')
        # Sempre (re)criar o script CLI para garantir versão atualizada
        criar_checkout_cli()

        # Executar Node.js
        result = subprocess.run(
            ['node', script_path, produto, str(valor_centavos), cliente_nome, cliente_telefone, str(validade_segundos), cliente_cpf],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode == 0:
            # Parse do resultado
            pix_data = json_lib.loads(result.stdout)

            if pix_data.get('success'):
                qr_code_url = pix_data['qr_code_url']
                pix_code = pix_data['pix_copia_cola']

                # Mensagem 1: PIX copia e cola
                msg_copia_cola = (
                    f"💰 *PIX Gerado!*\n\n"
                    f"📦 Produto: {produto}\n"
                    f"💵 Valor: R$ {valor_centavos/100:.2f}\n\n"
                    f"*PIX Copia e Cola:*\n`{pix_code}`"
                )
                send_text(numero_whatsapp, msg_copia_cola)

                # Mensagem 2: QR Code como mídia
                ok_media = send_media(
                    number=numero_whatsapp,
                    media_type="image",
                    file_name="qrcode_pix.png",
                    caption=f"🔳 Escaneie para pagar R$ {valor_centavos/100:.2f}",
                    media=qr_code_url
                )
                if not ok_media:
                    print("🔁 Tentando enviar o QR como documento...")
                    ok_media_doc = send_media(
                        number=numero_whatsapp,
                        media_type="document",
                        file_name="qrcode_pix.png",
                        caption=f"🔳 Escaneie para pagar R$ {valor_centavos/100:.2f}",
                        media=qr_code_url
                    )
                    ok_media = ok_media or ok_media_doc

                # Mensagem 3: validade
                expiracao_info = pix_data.get('expires_at') or ''
                msg_validade = (
                    f"⏳ Validade: 5 minutos ({validade_segundos} segundos)."
                    + (f"\nAté: {expiracao_info}" if expiracao_info else "")
                )
                send_text(numero_whatsapp, msg_validade)

                return jsonify({
                    "success": True,
                    "message": "PIX gerado e enviado com sucesso",
                    "pix_data": pix_data,
                    "validade_segundos": validade_segundos,
                    "ok_media": ok_media
                }), 200
            else:
                return jsonify({"error": "Falha ao gerar PIX", "details": pix_data}), 500
        else:
            return jsonify({"error": "Erro ao executar checkout.js", "stderr": result.stderr}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/obter-dados-pix/<numero>', methods=['GET'])
def obter_dados_pix(numero):
    """Endpoint para obter dados do pedido para gerar PIX"""
    try:
        dados = bot_simples.obter_dados_pix(numero)
        if dados:
            return jsonify({
                "status": "success",
                "data": {
                    "produto": dados["produto"],
                    "valor_centavos": dados["valor_centavos"],
                    "cliente_nome": dados.get("cliente_nome", "Cliente"),
                    "cliente_telefone": dados.get("cliente_telefone", numero),
                    "cliente_cpf": dados.get("cliente_cpf", "")
                }
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Dados do pedido não encontrados"
            }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def criar_checkout_cli():
    """Cria/Recria script CLI para chamar checkout.js com validade em segundos"""
    cli_content = """#!/usr/bin/env node
import { criarPixCheckout } from './checkout.js';

const [,, produtoNome, valorCentavos, clienteNome, clienteTelefone, expiresSeconds, clienteCpf] = process.argv;

criarPixCheckout(
    produtoNome,
    parseInt(valorCentavos),
    clienteNome,
    clienteTelefone,
    'cliente@email.com',
    clienteCpf || '',
    parseInt(expiresSeconds || '3600')
).then(result => {
    console.log(JSON.stringify(result));
    process.exit(0);
}).catch(error => {
    console.error(JSON.stringify({ success: false, error: error.message }));
    process.exit(1);
});
"""
    with open('checkout_cli.js', 'w') as f:
        f.write(cli_content)

# Rotas de teste de envio (diagnóstico)
@app.route('/test-send', methods=['POST'])
def test_send():
    try:
        data = request.get_json() or {}
        number = (data.get('number') or '').strip()
        text = (data.get('text') or '').strip()
        if not number or not text:
            return jsonify({"ok": False, "error": "Informe 'number' e 'text'"}), 400
        send_text(number, text)
        return jsonify({"ok": True, "message": "Envio de texto solicitado"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/test-media', methods=['POST'])
def test_media():
    try:
        data = request.get_json() or {}
        number = (data.get('number') or '').strip()
        media_type = (data.get('media_type') or 'image').strip()
        file_name = (data.get('file_name') or 'file.jpg').strip()
        caption = (data.get('caption') or '').strip()
        media = (data.get('media') or '').strip()  # URL ou base64
        if not number or not media:
            return jsonify({"ok": False, "error": "Informe 'number' e 'media'"}), 400
        ok = send_media(number, media_type, file_name, caption, media)
        return jsonify({"ok": ok, "message": "Envio de mídia solicitado"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/disparar-pix', methods=['GET'])
def disparar_pix_get():
    """Dispara um texto com PIX copia e cola e um QR para o número informado via querystring.
    Exemplo: GET /disparar-pix?number=5511993816036&valor_centavos=100&produto=Teste%20PIX
    """
    try:
        number = (request.args.get('number') or '').strip()
        produto = (request.args.get('produto') or 'Teste PIX').strip()
        valor_centavos = int(request.args.get('valor_centavos') or '100')
        if not number:
            return jsonify({"ok": False, "error": "Informe 'number' na query"}), 400

        # PIX copia e cola (exemplo fictício para envio; substitua por real se necessário)
        valor_reais = valor_centavos / 100.0
        copia_cola = (
            f"00020126330014BR.GOV.BCB.PIX0136pix-teste@example.com5204000053039865404{valor_reais:0.2f}" 
            f"5802BR5911{produto[:11]}6009Sao Paulo62070503***6304ABCD"
        )
        # QR Code baseado no copia e cola
        qr_code_url = (
            "https://api.qrserver.com/v1/create-qr-code/?size=512x512&data=" + copia_cola
        )

        # Mensagem 1: PIX copia e cola
        msg_copia_cola = (
            f"💰 *PIX Gerado!*\n\n"
            f"📦 Produto: {produto}\n"
            f"💵 Valor: R$ {valor_reais:.2f}\n\n"
            f"*PIX Copia e Cola:*\n`{copia_cola}`"
        )
        send_text(number, msg_copia_cola)
        ok_media = send_media(
            number=number,
            media_type="image",
            file_name="qrcode_pix.png",
            caption=f"🔳 Escaneie para pagar R$ {valor_reais:.2f}",
            media=qr_code_url
        )
        if not ok_media:
            print("🔁 Tentando enviar o QR como documento...")
            ok_media_doc = send_media(
                number=number,
                media_type="document",
                file_name="qrcode_pix.png",
                caption=f"🔳 Escaneie para pagar R$ {valor_reais:.2f}",
                media=qr_code_url
            )
            ok_media = ok_media or ok_media_doc

        # Mensagem 3: validade de 5 minutos
        send_text(number, "⏳ Validade: 5 minutos (300 segundos). Após isso, gere novamente.")

        return jsonify({
            "ok": True,
            "message": "PIX disparado",
            "numero": number,
            "produto": produto,
            "valor_centavos": valor_centavos,
            "qr_code_url": qr_code_url,
            "ok_media": ok_media
        }), 200
    except Exception as e:
        print(f"❌ Erro em /disparar-pix: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("=== App.py pronto em http://localhost:8001 ===")
    app.run(host='0.0.0.0', port=8001, debug=True)
def _normalize_number(number: str | None) -> str | None:
    """Normaliza número para formato E.164 sem sufixos de JID.
    - Remove qualquer sufixo após '@' (ex.: '@s.whatsapp.net', '@c.us', outros).
    - Remove espaços e caracteres não numéricos.
    - Mantém apenas dígitos (sem '+').
    """
    if not number:
        return None
    s = str(number).strip()
    if '@' in s:
        s = s.split('@', 1)[0]
    # Remover tudo que não seja dígito
    import re
    s = ''.join(re.findall(r'\d+', s))
    return s or None