# app/webhook_handler.py
import stripe
import os
import logging
from flask import Flask, request, jsonify # Ou FastAPI, Django, etc.
from app.config import settings
from database.db_utils import get_db, update_appointment_status, get_appointment_by_id
from database.models import AppointmentStatus # Importar o Enum
from utils.email_sender import send_email # Para enviar os emails de confirmação
from datetime import datetime, date, time # Importar para usar em details

app = Flask(__name__) # Ou inicie seu app FastAPI/Django

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

stripe.api_key = settings.STRIPE_API_KEY # É bom definir a chave aqui também

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

    # Lidar com os eventos
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        logging.info(f"Checkout Session Completed: {session['id']}")

        # Extrair dados do metadata. Esses dados foram definidos em stripe_tools.py
        appointment_id_str = session.get('metadata', {}).get('appointment_id')
        item_type_from_metadata = session.get('metadata', {}).get('item_type')
        client_email_from_metadata = session.get('metadata', {}).get('client_email')
        client_name_from_metadata = session.get('metadata', {}).get('client_name')
        client_phone_from_metadata = session.get('metadata', {}).get('client_phone')

        db_session = next(get_db())
        try:
            # Se for um agendamento de aula avulsa (tem appointment_id)
            if appointment_id_str and appointment_id_str != 'N/A':
                appointment_id = int(appointment_id_str)
                updated_appointment = update_appointment_status(db_session, appointment_id, AppointmentStatus.paid)
                db_session.commit()
                logging.info(f"Agendamento {appointment_id} atualizado para 'paid'.")

                if updated_appointment:
                    client_details = {
                        'client_name': updated_appointment.client_name,
                        'class_type': updated_appointment.class_type,
                        'appointment_date': updated_appointment.appointment_date,
                        'appointment_time': updated_appointment.appointment_time,
                        'client_phone': updated_appointment.client_phone,
                        'client_email': updated_appointment.client_email
                    }
                    # Enviar email de confirmação para o CLIENTE
                    send_email(
                        to_email=updated_appointment.client_email,
                        email_type='client_confirmation',  # Tipo pré-definido
                        appointment_details=client_details,
                        language='pt' # Ou a linguagem do cliente se você armazená-la
                    )
                    # Enviar email de confirmação para a EMPRESA
                    send_email(
                        to_email=settings.YOGA_KULA_NOTIFICATION_EMAIL,
                        email_type='company_paid_notification',  # Tipo pré-definido correto
                        appointment_details=client_details,
                        language='pt'
                    )
                    logging.info(f"Emails de confirmação enviados para agendamento {appointment_id}.")
                else:
                    logging.warning(f"Agendamento {appointment_id} não encontrado após pagamento confirmado via webhook.")

            # Se for compra de Pack/Mensalidade sem agendamento prévio
            elif item_type_from_metadata and client_email_from_metadata:
                purchase_details = {
                    'client_name': client_name_from_metadata,
                    'class_type': item_type_from_metadata, # O item comprado
                    'client_phone': client_phone_from_metadata,
                    'client_email': client_email_from_metadata,
                    'appointment_date': date.today(), # Data da compra
                    'appointment_time': time(0,0), # Hora genérica para compra de pack
                    'payment_status': 'Pago' # Indica que o pagamento foi feito
                }
                # Enviar email de confirmação para o CLIENTE (compra de pack/mensalidade)
                send_email(
                    to_email=client_email_from_metadata,
                    subject=f"Confirmação de Compra de {item_type_from_metadata} - Yoga Kula",
                    appointment_details=purchase_details,
                    language='pt'
                )
                # Enviar email de confirmação para a EMPRESA (compra de pack/mensalidade)
                send_email(
                    to_email=settings.YOGA_KULA_NOTIFICATION_EMAIL,
                    subject=f"CONFIRMAÇÃO: Nova Compra de {item_type_from_metadata} - Yoga Kula",
                    appointment_details=purchase_details,
                    language='pt'
                )
                logging.info(f"Emails de confirmação enviados para compra de {item_type_from_metadata} por {client_name_from_metadata}.")

        except Exception as e:
            db_session.rollback()
            logging.error(f"Erro ao processar checkout.session.completed para agendamento/compra: {e}", exc_info=True)
        finally:
            db_session.close()

    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    # Isso é apenas para testar o webhook localmente.
    # Em produção, você rodará isso através de um WSGI server (Gunicorn, uWSGI)
    # e usará um proxy reverso (Nginx) ou um serviço como Ngrok para expor.
    # Certifique-se de que esta porta não entra em conflito com outras aplicações.
    app.run(port=4242)