from flask import Flask, request, jsonify
import json
from datetime import datetime
import requests

app = Flask(__name__)

class EvolutionWebhookProcessor:
    def __init__(self):
        self.log_file = "evolution_messages.log"
    
    def process_event(self, payload):
        """Processa eventos da Evolution API"""
        event_type = payload.get('event')
        instance = payload.get('instance')
        data = payload.get('data', {})
        
        print(f"\n{'='*60}")
        print(f"📱 EVOLUTION API - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"🎯 EVENTO: {event_type}")
        print(f"📡 INSTÂNCIA: {instance}")
        
        # Processar baseado no tipo de evento
        if event_type == "message":
            self._process_message(data, instance)
        elif event_type == "contacts.update":
            self._process_contact_update(data, instance)
        elif event_type == "messages.upsert":
            self._process_message_upsert(data, instance)
        elif event_type == "chats.update":
            self._process_chat_update(data, instance)
        else:
            print(f"🔍 Evento não tratado: {event_type}")
            print(f"📦 Dados: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Salvar log
        self._save_log(event_type, instance, data)

        print(f"{'='*60}")
        print("✅ EVENTO PROCESSADO")
        print(f"{'='*60}\n")

    def _process_message(self, data, instance):
        """Processa evento de mensagem"""
        print("💬 MENSAGEM RECEBIDA:")
        from_number = data.get('from', '').replace('@s.whatsapp.net', '').replace('@c.us', '')
        message_text = data.get('body', '')
        message_type = data.get('type', 'text')
        message_id = data.get('id', '')
        print(f"   👤 DE: {from_number}")
        print(f"   💬 TEXTO: {message_text}")
        print(f"   🎯 TIPO: {message_type}")
        print(f"   🆔 ID: {message_id}")
        if message_type in ['image', 'video', 'document', 'audio']:
            media_info = data.get('media', {})
            print(f"   📷 MÍDIA: {media_info.get('url', 'N/A')}")

    def _process_contact_update(self, data, instance):
        """Processa atualização de contato"""
        print("👤 ATUALIZAÇÃO DE CONTATO:")
        contact_id = data.get('id', '').replace('@s.whatsapp.net', '')
        profile_picture = data.get('profilePictureUrl', 'N/A')
        print(f"   📞 CONTATO: {contact_id}")
        print(f"   🖼️ FOTO: {profile_picture}")
        print(f"   👤 DONO: {data.get('owner', 'N/A')}")

    def _process_message_upsert(self, data, instance):
        """Processa messages.upsert (estrutura Baileys) – suporta data.messages (lista) e item único."""
        print("📨 MENSAGEM UPSERT:")
        try:
            msgs = data.get('messages') if isinstance(data, dict) else None
            if isinstance(msgs, list) and msgs:
                for idx, item in enumerate(msgs):
                    key = item.get('key', {})
                    message_data = item.get('message', {})
                    from_jid = key.get('remoteJid', '').replace('@s.whatsapp.net', '')
                    from_me = key.get('fromMe', False)
                    print(f"   [{idx}] 👤 DE: {from_jid} | 🤖 fromMe: {from_me}")
                    if 'conversation' in message_data:
                        print(f"   [{idx}] 💬 TEXTO: {message_data['conversation']}")
                    elif 'extendedTextMessage' in message_data:
                        print(f"   [{idx}] 💬 TEXTO: {message_data['extendedTextMessage'].get('text', '')}")
                    else:
                        print(f"   [{idx}] 📦 MENSAGEM: {json.dumps(message_data, indent=2, ensure_ascii=False)}")
            else:
                key = data.get('key', {})
                message_data = data.get('message', {})
                from_jid = key.get('remoteJid', '').replace('@s.whatsapp.net', '')
                from_me = key.get('fromMe', False)
                print(f"   👤 DE: {from_jid}")
                print(f"   🤖 ENVIADA POR MIM: {from_me}")
                if 'conversation' in message_data:
                    print(f"   💬 TEXTO: {message_data['conversation']}")
                elif 'extendedTextMessage' in message_data:
                    print(f"   💬 TEXTO: {message_data['extendedTextMessage'].get('text', '')}")
                else:
                    print(f"   📦 MENSAGEM: {json.dumps(message_data, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"   ⚠️ Falha ao processar messages.upsert: {e}")

    def _process_chat_update(self, data, instance):
        """Processa atualização de chat"""
        print("💬 ATUALIZAÇÃO DE CHAT:")
        print(f"   📦 DADOS: {json.dumps(data, indent=2, ensure_ascii=False)}")

    def _save_log(self, event_type, instance, data):
        """Salva log em arquivo"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] {event_type} - {instance}\n")
            if event_type == "message":
                from_number = data.get('from', '').replace('@s.whatsapp.net', '')
                message_text = data.get('body', '')
                f.write(f"   {from_number}: {message_text}\n")
            elif event_type == "contacts.update":
                contact_id = data.get('id', '').replace('@s.whatsapp.net', '')
                f.write(f"   Contato atualizado: {contact_id}\n")

def forward_to_app(payload, source_path: str = "webhook"):
    """Encaminha o payload recebido para o App.py para processamento/resposta."""
    try:
        url = "http://localhost:8001/process-event"
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers, timeout=8)
        if resp.status_code < 300:
            print(f"➡️ Encaminhado para App.py ({url}) [{resp.status_code}]")
        else:
            print(f"⚠️ Falha ao encaminhar para App.py ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Erro ao encaminhar para App.py: {e}")

# Instância do processador
processor = EvolutionWebhookProcessor()

@app.route('/webhook', methods=['POST'])
@app.route('/<path:endpoint>', methods=['POST'])
def webhook_handler(endpoint="webhook"):
    """Handler principal para Evolution API"""
    try:
        if request.is_json:
            payload = request.get_json()

            # Derivar 'event' do path quando não enviado no corpo
            if endpoint and isinstance(payload, dict) and 'event' not in payload:
                path = endpoint.strip().lower()
                event_map = {
                    'messages-upsert': 'messages.upsert',
                    'chats-update': 'chats.update',
                    'contacts-update': 'contacts.update',
                }
                derived_event = event_map.get(path, path)
                payload['event'] = derived_event

            processor.process_event(payload)
            forward_to_app(payload, source_path=endpoint or 'webhook')
        else:
            print("❌ Payload não é JSON")

        return jsonify({"status": "success", "message": "Webhook received"}), 200
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({"status": "error"}), 200

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "running", "timestamp": datetime.now().isoformat()})

@app.route('/logs', methods=['GET'])
def show_logs():
    """Mostra logs das mensagens"""
    try:
        with open("evolution_messages.log", "r", encoding="utf-8") as f:
            logs = f.readlines()[-20:]  # Últimas 20 linhas
        return jsonify({"logs": logs})
    except:
        return jsonify({"logs": ["Nenhum log disponível"]})

if __name__ == '__main__':
    print("=" * 50)
    print("EVOLUTION WEBHOOK - OTIMIZADO")
    print("Pronto para receber mensagens!")
    print("Envie uma mensagem no WhatsApp e veja os detalhes")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5001, debug=True)
 
