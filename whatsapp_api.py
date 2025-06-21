# whatsapp_api.py
from flask import Flask, request
import os
import sys
from twilio.twiml.messaging_response import MessagingResponse # Se usar Twilio
from twilio.rest import Client # Se usar Twilio

# Adiciona o diretório raiz do projeto ao sys.path para importar app.agent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.agent import initialize_agent, get_session_history # Importa seu agente e histórico
from app.config import settings # Importa suas configurações para API Keys, etc.

app = Flask(__name__)

# Configurações do Twilio (exemplo) - obter do seu .env
# account_sid = settings.TWILIO_ACCOUNT_SID
# auth_token = settings.TWILIO_AUTH_TOKEN
# twilio_client = Client(account_sid, auth_token)

# Inicializa o agente uma vez na inicialização da aplicação
agent_executor = initialize_agent()

@app.route("/webhook", methods=["POST"])
def webhook():
    # Este é um exemplo para Twilio. Outros BSPs terão payloads JSON diferentes.
    # Você precisará adaptar a forma de extrair a mensagem e o remetente.
    incoming_msg = request.values.get('Body', '').lower()
    sender_id = request.values.get('From', '') # Formato: whatsapp:+55119XXXXXXXX
    
    # Extrai apenas o número do telefone para usar como session_id
    if sender_id.startswith("whatsapp:"):
        session_id = sender_id.split(":")[-1]
    else:
        session_id = sender_id # Caso seja outro tipo de remetente ou formato
    
    print(f"Mensagem recebida de {session_id}: {incoming_msg}")

    # Processa a mensagem com o agente
    try:
        response = agent_executor.invoke(
            {"input": incoming_msg},
            config={"configurable": {"session_id": session_id}}
        )
        bot_response_text = response['output']
    except Exception as e:
        print(f"Erro ao processar mensagem com o agente: {e}")
        bot_response_text = "Desculpe, tive um problema para processar sua solicitação. Por favor, tente novamente mais tarde."

    # Envia a resposta de volta ao WhatsApp (exemplo com Twilio)
    # response_twilio = MessagingResponse()
    # response_twilio.message(bot_response_text)
    # return str(response_twilio)

    # Se não usar Twilio TwiML, você faria uma chamada POST para a API do seu BSP
    # Exemplo genérico (adaptar para o BSP específico)
    # headers = {"Authorization": f"Bearer SEU_BSP_API_KEY", "Content-Type": "application/json"}
    # payload = {
    #     "to": sender_id,
    #     "type": "text",
    #     "text": {"body": bot_response_text}
    # }
    # import requests
    # requests.post("URL_DA_API_DE_ENVIO_DO_BSP", json=payload, headers=headers)
    # return "OK", 200 # Resposta HTTP para o webhook

    # Para testes iniciais sem BSP configurado, apenas printar e retornar OK
    return "OK", 200


if __name__ == "__main__":
    # Para testar localmente, use ngrok para expor este webhook
    # ngrok http 5000
    print("Iniciando Flask app...")
    app.run(debug=True, port=5000)