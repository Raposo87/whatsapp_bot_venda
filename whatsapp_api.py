# whatsapp_api.py
from flask import Flask, request, jsonify # Importe jsonify
import os
import sys
import logging # Importar logging
# from twilio.twiml.messaging_response import MessagingResponse # REMOVER
# from twilio.rest import Client # REMOVER

# Adiciona o diretório raiz do projeto ao sys.path para importar app.agent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Garante que as importações dentro de 'app' funcionem bem

from app.agent import initialize_agent # Importa seu agente
from app.config import settings # Importa suas configurações para API Keys, etc.
from utils.whatsapp_sender import send_whatsapp_message # Importa a função para enviar mensagens
from utils.language_detector import detect_language # Importa o detector de idioma

app = Flask(__name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Inicializa o agente uma vez na inicialização da aplicação
agent_executor = initialize_agent()
logging.info("Agente de IA inicializado.")

# Endpoint para verificação do webhook do WhatsApp
@app.route("/webhook", methods=["GET"])
def whatsapp_webhook_verify():
    """
    Endpoint para a verificação do webhook do WhatsApp.
    Meta envia um GET request com um 'hub.verify_token' e 'hub.challenge'.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            logging.warning(f"Falha na verificação do webhook. Token ou modo inválido. Mode: {mode}, Token: {token}")
            return jsonify({"error": "Verification failed"}), 403
    logging.warning("Requisição GET sem parâmetros hub.mode ou hub.verify_token.")
    return jsonify({"error": "Missing parameters"}), 400

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook_handle_message():
    """
    Endpoint para receber mensagens POST do WhatsApp Cloud API.
    """
    data = request.get_json()
    logging.info(f"Dados recebidos do WhatsApp: {data}")

    # Verifica se o evento é uma mensagem do WhatsApp
    if data and "object" in data and data["object"] == "whatsapp_business_account":
        try:
            for entry in data["entry"]:
                for change in entry["changes"]:
                    if change["field"] == "messages":
                        for message in change["value"]["messages"]:
                            # Apenas processa mensagens de texto
                            if message["type"] == "text":
                                incoming_msg = message["text"]["body"]
                                sender_id = message["from"] # Número do remetente
                                # O WhatsApp Cloud API usa 'from' no formato '55119XXXXXXXX'
                                # Para o histórico de sessão, é melhor usar um formato consistente, talvez com '+'
                                # Ou apenas o número puro, desde que seja único.
                                session_id = "+" + sender_id # Adiciona o '+' de volta para consistência se necessário

                                logging.info(f"Mensagem recebida de {sender_id}: {incoming_msg}")

                                # Detecta o idioma da mensagem
                                detected_language = detect_language(incoming_msg)
                                logging.info(f"Idioma detectado: {detected_language}")

                                # Processa a mensagem com o agente
                                try:
                                    response = agent_executor.invoke(
                                        {"input": incoming_msg, "language": detected_language}, # Passa o idioma para o agente
                                        config={"configurable": {"session_id": session_id}}
                                    )
                                    bot_response_text = response['output']
                                    logging.info(f"Resposta do agente: {bot_response_text}")
                                except Exception as e:
                                    logging.error(f"Erro ao processar mensagem com o agente para {session_id}: {e}", exc_info=True)
                                    bot_response_text = "Desculpe, tive um problema para processar sua solicitação. Por favor, tente novamente mais tarde."

                                # Envia a resposta de volta ao WhatsApp
                                success = send_whatsapp_message(to_phone_number=session_id, message_body=bot_response_text)
                                if success:
                                    logging.info(f"Mensagem enviada com sucesso para {session_id}.")
                                else:
                                    logging.error(f"Falha ao enviar mensagem para {session_id}.")

                            else:
                                logging.info(f"Tipo de mensagem não suportado: {message['type']}")
                                # Opcional: enviar uma mensagem para o usuário informando que o tipo de mensagem não é suportado
                                # send_whatsapp_message(message["from"], "Desculpe, só consigo processar mensagens de texto no momento.")

        except Exception as e:
            logging.error(f"Erro ao processar payload do WhatsApp: {e}", exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500

    return jsonify({'status': 'success'}), 200 # Sempre retorne 200 OK para o WhatsApp

if __name__ == '__main__':
    # Cria o banco de dados e as tabelas na inicialização, se não existirem
    from database.db_utils import create_db_and_tables
    print("Verificando/criando banco de dados e tabelas...")
    create_db_and_tables()
    print("Banco de dados e tabelas verificados/criados.")

    # Para rodar com ngrok em ambiente de desenvolvimento:
    # ngrok http 5000
    # O Flask roda na porta 5000 por padrão.
    app.run(host='0.0.0.0', port=5000, debug=True) # Rode em modo de depuração para ver logs no console