"""
Script para configurar webhook do Evolution API
Configura webhook para receber MESSAGES_UPSERT no mesmo endpoint
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Configurações
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME", "Bot1")
API_KEY = os.getenv("API_KEY_EVOLUTION", "429683C4C977415CAAFCCE10F7D57E11")
WEBHOOK_URL = "https://4e7ce602c00a.ngrok-free.app"

url = f"{EVOLUTION_API_URL}/webhook/set/{INSTANCE_NAME}"

payload = {
    "webhook": {
        "enabled": True,
        "url": f"{WEBHOOK_URL}/process-event",
        "webhookByEvents": False,  # IMPORTANTE: False para enviar tudo para mesma URL
        "webhookBase64": True,
        "events": [
            "MESSAGES_UPSERT",  # Mensagens recebidas
            "CONNECTION_UPDATE"  # Status da conexão
        ]
    }
}

headers = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

print("Configurando webhook...")
print(f"URL: {url}")
print(f"Payload: {payload}")
print()

try:
    response = requests.post(url, json=payload, headers=headers, timeout=10)

    print(f"Status: {response.status_code}")
    print(f"Resposta:")
    print(response.json())

    if response.status_code in (200, 201):
        print("\nWebhook configurado com sucesso!")
        print(f"Webhook URL: {payload['webhook']['url']}")
        print(f"Eventos: {', '.join(payload['webhook']['events'])}")
        print(f"webhookByEvents: {payload['webhook']['webhookByEvents']}")
    else:
        print("\nErro ao configurar webhook")

except Exception as e:
    print(f"Erro: {e}")
 
