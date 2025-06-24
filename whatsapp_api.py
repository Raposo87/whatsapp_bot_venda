# whatsapp_api.py
from flask import Flask, request, jsonify
import os
import sys
import stripe
import logging
from datetime import datetime, date, time
# from twilio.twiml.messaging_response import MessagingResponse # Removido, pois você não está usando Twilio TwiML

# Adiciona o diretório raiz do projeto ao sys.path para importar app.agent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.agent import initialize_agent, get_session_history
from app.config import settings
from database.db_utils import get_db, update_appointment_status, get_appointment_by_id
from database.models import AppointmentStatus
from utils.email_sender import send_email # Para enviar os emails de confirmação
from utils.language_detector import detect_language # <--- ADICIONADO: Importação do detector de idioma
from utils.whatsapp_sender import send_whatsapp_message # <--- ADICIONADO: Importação para enviar mensagens WhatsApp


app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração do Stripe
stripe.api_key = settings.STRIPE_API_KEY
YOUR_COMMISSION_RATE = 0.10 # 10%

# Inicializa o agente uma vez na inicialização da aplicação
agent_executor = initialize_agent()

logging.info(f"DEBUG: OPENAI_API_KEY que está sendo usada: {settings.OPENAI_API_KEY[:5]}...{settings.OPENAI_API_KEY[-5:]} (verifique as 5 primeiras e últimas letras)")

# --- Rota para o Webhook do WHATSAPP ---
@app.route("/webhook", methods=["GET", "POST"]) # Adicionado GET para verificação do Meta
def whatsapp_webhook():
    # Lógica de VERIFICAÇÃO do Webhook da Meta
    if request.method == "GET":
        # Parâmetros de verificação da Meta
        verify_token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
            logging.info("Webhook WhatsApp verificado com sucesso!")
            return challenge, 200
        else:
            logging.warning(f"Falha na verificação do Webhook WhatsApp. Token recebido: {verify_token}")
            return "Verification token mismatch", 403

    # Lógica de RECEBIMENTO de Mensagens do WhatsApp (POST)
    elif request.method == "POST":
        data = request.json
        logging.info(f"Dados do Webhook WhatsApp recebidos: {data}")

        try:
            # Percorrer entries -> changes -> value -> messages
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        for message in change.get('value', {}).get('messages', []):
                            if message.get('type') == 'text':
                                incoming_msg = message['text']['body']
                                from_phone_number = message['from'] # Número do remetente
                                logging.info(f"Mensagem recebida de {from_phone_number}: {incoming_msg}")

                                session_id = from_phone_number # Use o número como session_id

                                # --- ADICIONADO: DETECÇÃO DE IDIOMA ---
                                detected_language = detect_language(incoming_msg)
                                logging.info(f"Idioma detectado para '{incoming_msg}': {detected_language}")
                                # --- FIM DA ADIÇÃO ---

                                try:
                                    response = agent_executor.invoke(
                                        {"input": incoming_msg, "language": detected_language}, # <--- AGORA PASSA 'language'
                                        config={"configurable": {"session_id": session_id}}
                                    )
                                    bot_response_text = response['output']
                                    logging.info(f"Resposta do bot para {from_phone_number}: {bot_response_text}")

                                    # Enviar a resposta de volta via WhatsApp Cloud API
                                    send_whatsapp_message(from_phone_number, bot_response_text)

                                except Exception as e:
                                    logging.error(f"Erro ao processar mensagem com o agente para {from_phone_number}: {e}", exc_info=True)
                                    error_response = "Desculpe, tive um problema para processar sua solicitação. Por favor, tente novamente mais tarde."
                                    send_whatsapp_message(from_phone_number, error_response) # Tentar enviar erro

        except Exception as e:
            logging.error(f"Erro ao analisar payload do WhatsApp webhook: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': 'Failed to process WhatsApp message'}), 500

        return jsonify({'status': 'success'}), 200 # Responder OK para o Meta

# --- Rota para o Webhook do STRIPE ---
@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('stripe-signature')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logging.error(f"Erro de payload no webhook Stripe: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logging.error(f"Erro de assinatura no webhook Stripe: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    db_session = get_db()
    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            logging.info(f"Checkout Session Completed: {session['id']}")

            appointment_id = session.metadata.get('appointment_id')
            item_type = session.metadata.get('item_type')
            client_name = session.metadata.get('client_name')
            client_email = session.metadata.get('client_email')
            client_phone = session.metadata.get('client_phone')

            amount_total_in_cents = session.get('amount_total')
            currency = session.get('currency', 'eur')

            if amount_total_in_cents is None:
                logging.warning(f"amount_total não encontrado na sessão {session['id']}. Não é possível registrar o valor.")
                amount_paid = 0.0
            else:
                amount_paid = amount_total_in_cents / 100.0

            commission_amount = amount_paid * YOUR_COMMISSION_RATE

            logging.info(f"Pagamento de {amount_paid:.2f} {currency.upper()} para {item_type}. Comissão calculada: {commission_amount:.2f} {currency.upper()}")

            if appointment_id:
                try:
                    appointment_id_int = int(appointment_id)
                    updated_appointment = update_appointment_status(
                        db_session,
                        appointment_id_int,
                        AppointmentStatus.paid,
                        amount_paid=amount_paid,
                        commission_amount=commission_amount
                    )
                    if updated_appointment:
                        logging.info(f"Agendamento {appointment_id_int} atualizado para 'pago' e valores registrados.")
                        appointment_details = {
                            "client_name": updated_appointment.client_name,
                            "client_email": updated_appointment.client_email,
                            "client_phone": updated_appointment.client_phone,
                            "class_type": updated_appointment.class_type,
                            "appointment_date": updated_appointment.appointment_date,
                            "appointment_time": updated_appointment.appointment_time,
                            "status": updated_appointment.status.value,
                            "amount_paid": updated_appointment.amount_paid,
                            "commission_amount": updated_appointment.commission_amount,
                            "item_type": item_type
                        }
                        send_email(
                            to_email=appointment_details["client_email"],
                            subject=f"Confirmação de Agendamento e Pagamento - Yoga Kula ({appointment_details['class_type']})",
                            appointment_details=appointment_details,
                            language='pt'
                        )
                        send_email(
                            to_email=settings.YOGA_KULA_NOTIFICATION_EMAIL,
                            subject=f"CONFIRMAÇÃO: Novo Agendamento Pago - {appointment_details['class_type']} - Yoga Kula",
                            appointment_details=appointment_details,
                            language='pt'
                        )
                        logging.info(f"Emails de confirmação de agendamento enviados para {appointment_details['client_email']} e para a empresa.")
                    else:
                        logging.error(f"Agendamento com ID {appointment_id_int} não encontrado para atualização.")
                except ValueError:
                    logging.error(f"appointment_id '{appointment_id}' não é um inteiro válido.")
                except Exception as e:
                    logging.error(f"Erro específico ao processar agendamento pago: {e}", exc_info=True)
            else:
                logging.info(f"Compra de {item_type} registrada sem agendamento específico.")
                purchase_details = {
                    "item_type": item_type,
                    "client_name": client_name,
                    "client_email": client_email,
                    "client_phone": client_phone,
                    "amount_paid": amount_paid,
                    "commission_amount": commission_amount,
                    "purchase_date": datetime.now().date(),
                    "purchase_time": datetime.now().time()
                }
                send_email(
                    to_email=client_email,
                    subject=f"Confirmação de Compra de {item_type} - Yoga Kula",
                    appointment_details=purchase_details,
                    language='pt'
                )
                send_email(
                    to_email=settings.YOGA_KULA_NOTIFICATION_EMAIL,
                    subject=f"CONFIRMAÇÃO: Nova Compra de {item_type} - Yoga Kula",
                    appointment_details=purchase_details,
                    language='pt'
                )
                logging.info(f"Emails de confirmação enviados para compra de {item_type} por {client_name}.")

        elif event['type'] == 'payment_intent.succeeded':
            logging.info(f"Payment Intent Succeeded: {event['data']['object']['id']}")
        else:
            logging.info(f"Evento Stripe não tratado: {event['type']}")

    except Exception as e:
        db_session.rollback()
        logging.error(f"Erro ao processar webhook Stripe para evento {event['type']}: {e}", exc_info=True)
    finally:
        db_session.close()

    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    from database.db_utils import create_db_and_tables
    print("Verificando/criando banco de dados e tabelas...")
    create_db_and_tables()
    print("Banco de dados e tabelas verificados/criados.")
    app.run(host='0.0.0.0', port=5000, debug=True)