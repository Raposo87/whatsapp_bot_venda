# whatsapp_api.py
from utils.whatsapp_sender import send_whatsapp_message
from utils.language_detector import detect_language
from utils.email_sender import send_email
from database.models import AppointmentStatus
from database.db_utils import get_db, update_appointment_status_only, get_appointment_by_id, update_appointment_payment_link
from app.config import settings
from app.agent import initialize_agent, get_session_history
from flask import Flask, request, jsonify
import os
import sys
import stripe
import logging
from datetime import datetime, date, time
import re

# Adiciona o diretório raiz do projeto ao sys.path para importar app.agent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))


app = Flask(__name__)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração do Stripe
stripe.api_key = settings.STRIPE_API_KEY
YOUR_COMMISSION_RATE = 0.10  # 10%

# Inicializa o agente uma vez na inicialização da aplicação
agent_executor = initialize_agent()

logging.info(
    f"DEBUG: OPENAI_API_KEY que está sendo usada: {settings.OPENAI_API_KEY[:2]}...{settings.OPENAI_API_KEY[-5:]} (verifique as 5 primeiras e últimas letras)")


# --- Função de utilidade para validação de e-mail ---
def is_valid_email(email: str) -> bool:
    """Verifica se o formato do e-mail é válido."""
    # Regex para validar e-mails (pode ser ajustado para mais ou menos rigor)
    # Este regex cobre a maioria dos casos válidos.
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(email_regex, email) is not None

# --- Rota para o Webhook do WHATSAPP ---


@app.route("/webhook", methods=["GET", "POST"])
def whatsapp_webhook():
    try:
        # Lógica de VERIFICAÇÃO do Webhook da Meta (para configurar o webhook)
        if request.method == "GET":
            VERIFY_TOKEN = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
            mode = request.args.get("hub.mode")
            token = request.args.get("hub.verify_token")
            challenge = request.args.get("hub.challenge")

            if mode and token:
                if mode == "subscribe" and token == VERIFY_TOKEN:
                    logging.info("WEBHOOK_VERIFIED")
                    return challenge, 200
                else:
                    logging.warning(
                        "WhatsApp Webhook: Verification token mismatch.")
                    return jsonify({"status": "Verification token mismatch"}), 403
            else:
                logging.warning(
                    "WhatsApp Webhook: Missing parameters for verification.")
                return jsonify({"status": "Missing parameters"}), 400

        # Lógica para receber e processar mensagens WhatsApp
        if request.method == "POST":
            data = request.get_json()
            logging.info(f"Received WhatsApp webhook data: {data}")

            if "object" in data and "entry" in data:
                for entry in data["entry"]:
                    for change in entry["changes"]:
                        if "value" in change and "messages" in change["value"]:
                            for message in change["value"]["messages"]:
                                if message["type"] == "text":
                                    from_number = message["from"]
                                    msg_body = message["text"]["body"]
                                    logging.info(
                                        f"Mensagem de {from_number}: {msg_body}")

                                    try:
                                        # Detecta o idioma antes de invocar o agente
                                        detected_language = detect_language(
                                            msg_body)
                                        session_id = from_number  # Usar o número do remetente como session_id

                                        response_content = agent_executor.invoke(
                                            {"input": msg_body,
                                                "language": detected_language},
                                            config={"configurable": {
                                                "session_id": session_id}}
                                        )
                                        agent_response = response_content.get(
                                            'output', 'Desculpe, não consegui processar sua solicitação.')

                                        final_whatsapp_response_for_chat = agent_response

                                        # Verifica se a resposta contém o padrão de confirmação de agendamento com link de pagamento
                                        match_id = re.search(
                                            r"AGENDA_CONFIRMED_WITH_PAYMENT:(\d+)", agent_response)
                                        if match_id:
                                            appointment_id = int(
                                                match_id.group(1))
                                            db_session = None  # Inicializa para garantir que é sempre fechado
                                            try:
                                                # Abre uma nova sessão de DB
                                                db_session = next(get_db())
                                                appointment = get_appointment_by_id(
                                                    db_session, appointment_id)

                                                if appointment and appointment.stripe_payment_link:
                                                    # Reconstruir a mensagem para incluir o link de pagamento no chat
                                                    if detected_language == 'pt':
                                                        final_whatsapp_response_for_chat = (
                                                            f"A sua aula de {appointment.class_type} foi agendada com sucesso para "
                                                            f"o dia {appointment.appointment_date.strftime('%d-%m-%Y')} às {appointment.appointment_time.strftime('%H:%M')}. "
                                                            f"Para confirmar a sua reserva, por favor, finalize o pagamento através do link: "
                                                            f"[Pagar aqui!]({appointment.stripe_payment_link})"
                                                        )
                                                    else:  # Inglês ou outro idioma padrão
                                                        final_whatsapp_response_for_chat = (
                                                            f"Your {appointment.class_type} class is successfully scheduled for "
                                                            f"{appointment.appointment_date.strftime('%Y-%m-%d')} at {appointment.appointment_time.strftime('%H:%M')}. "
                                                            f"To confirm your booking, please complete the payment via the link: "
                                                            f"[Pay here!]({appointment.stripe_payment_link})"
                                                        )
                                                    logging.info(
                                                        f"Link de pagamento inserido na resposta do WhatsApp para {from_number}.")

                                                    # --- ENVIAR EMAIL DE CONFIRMAÇÃO COM LINK DE PAGAMENTO PARA O CLIENTE ---
                                                    if appointment.client_email and is_valid_email(appointment.client_email):
                                                        email_details_client = {
                                                            'client_name': appointment.client_name,
                                                            'class_type': appointment.class_type,
                                                            'appointment_date': appointment.appointment_date,
                                                            'appointment_time': appointment.appointment_time,
                                                        }
                                                        try:
                                                            send_email(
                                                                to_email=appointment.client_email,
                                                                email_type='company_pending_notification',
                                                                appointment_details=email_details_client,
                                                                language=detected_language
                                                            )
                                                            logging.info(
                                                                f"Email de confirmação com link de pagamento enviado para {appointment.client_email}.")
                                                        except Exception as email_err:
                                                            logging.error(
                                                                f"Erro ao enviar email de link de pagamento para o cliente {appointment.client_email}: {email_err}", exc_info=True)
                                                    else:
                                                        logging.warning(
                                                            f"Não foi possível enviar email ao cliente {appointment.client_email} para agendamento {appointment_id}: email inválido ou ausente.")

                                                    # --- ENVIAR EMAIL DE NOTIFICAÇÃO DE AGENDAMENTO PENDENTE PARA A EMPRESA ---
                                                    if settings.YOGA_KULA_NOTIFICATION_EMAIL and is_valid_email(settings.YOGA_KULA_NOTIFICATION_EMAIL):
                                                        email_details_company = {
                                                            'client_name': appointment.client_name,
                                                            'class_type': appointment.class_type,
                                                            'appointment_date': appointment.appointment_date,
                                                            'appointment_time': appointment.appointment_time,
                                                            'client_phone': appointment.client_phone,
                                                            'client_email': appointment.client_email,
                                                        }
                                                        try:
                                                            send_email(
                                                                to_email=settings.YOGA_KULA_NOTIFICATION_EMAIL,
                                                                email_type='company_pending_notification',
                                                                appointment_details=email_details_company,
                                                                language='pt'  # Idioma fixo para notificação da empresa
                                                            )
                                                            logging.info(
                                                                f"Email de notificação de agendamento PENDENTE de pagamento enviado para a empresa.")
                                                        except Exception as email_err:
                                                            logging.error(
                                                                f"Erro ao enviar email de notificação PENDENTE para a empresa: {email_err}", exc_info=True)
                                                    else:
                                                        logging.error(
                                                            f"Email de notificação da empresa ({settings.YOGA_KULA_NOTIFICATION_EMAIL}) é inválido ou ausente.")

                                                else:
                                                    logging.warning(
                                                        f"Agendamento {appointment_id} encontrado, mas link de pagamento não disponível ou agendamento nulo.")
                                                    final_whatsapp_response_for_chat = "Desculpe, a sua aula foi agendada, mas não consegui gerar o link de pagamento. Por favor, entre em contacto direto com o estúdio."

                                            except ValueError as ve:
                                                logging.error(
                                                    f"Erro de valor ao processar agendamento {appointment_id}: {ve}", exc_info=True)
                                                final_whatsapp_response_for_chat = "Desculpe, ocorreu um erro de dados ao finalizar o agendamento da sua aula. Por favor, tente novamente ou entre em contacto direto com o estúdio."
                                            except Exception as e:
                                                logging.error(
                                                    f"Erro inesperado ao processar agendamento {appointment_id} ou enviar email/link: {e}", exc_info=True)
                                                final_whatsapp_response_for_chat = "Desculpe, ocorreu um erro ao finalizar o agendamento da sua aula. Por favor, tente novamente ou entre em contacto direto com o estúdio."
                                            finally:
                                                if db_session:
                                                    db_session.close()  # Sempre fechar a sessão do DB

                                        send_whatsapp_message(
                                            from_number, final_whatsapp_response_for_chat)
                                        logging.info(
                                            f"Resposta do agente enviada para {from_number}: {final_whatsapp_response_for_chat}")

                                    except Exception as e:
                                        logging.error(
                                            f"Erro ao processar mensagem do WhatsApp para {from_number}: {e}", exc_info=True)
                                        send_whatsapp_message(
                                            from_number, "Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente mais tarde.")

                                elif message["type"] == "button":
                                    logging.info(
                                        f"Botão clicado de {message['from']}: {message['button']['text']}")
                                    # Lógica para botões se necessário
                                    pass

                        if "statuses" in change["value"]:
                            for status in change["value"]["statuses"]:
                                logging.info(
                                    f"Status da mensagem recebido: ID={status['id']}, Status={status['status']}, Recipient={status['recipient_id']}")

            return jsonify({"status": "success"}), 200
    except Exception as general_error:
        logging.critical(
            f"Erro crítico não tratado no webhook do WhatsApp: {general_error}", exc_info=True)
        return jsonify({"status": "Internal server error"}), 500


# --- Rota para o Webhook do STRIPE ---
@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("stripe-signature")
    event = None
    db_session_generator = None
    db_session = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logging.error(f"Erro de ValueError no payload do webhook Stripe: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logging.error(
            f"Erro de SignatureVerificationError no webhook Stripe: {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    except Exception as e:
        logging.error(
            f"Erro inesperado ao construir evento Stripe: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error during event construction'}), 500

    try:
        db_session_generator = get_db()
        # Obtém a sessão do banco de dados
        db_session = next(db_session_generator)

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            client_email = session.get('customer_details', {}).get('email')

            # Priorizar o nome dos metadados (nome real do banco de dados) em vez do customer_details
            client_name = session.get('metadata', {}).get(
                'client_name', 'Cliente')
            if not client_name or client_name == 'N/A':
                # Fallback para customer_details se não houver nos metadados
                client_name = session.get(
                    'customer_details', {}).get('name', 'Cliente')

            item_type = "N/A"  # Default value
            appointment_id_str = None  # Store as string initially

            # Priorize retrieving item_type from line_items data
            if 'line_items' in session and session['line_items'] and session['line_items']['data']:
                price_id = session['line_items']['data'][0]['price']['id']
                for key, value in settings.STRIPE_PRICE_IDS.items():
                    if value == price_id:
                        item_type = key
                        break

            # Fallback to metadata if item_type not found in line_items
            if item_type == "N/A" and 'metadata' in session:
                item_type = session['metadata'].get('item_type', 'N/A')
                appointment_id_str = session['metadata'].get('appointment_id')

            logging.info(
                f"Checkout Session Completed para {item_type} (Agendamento ID bruto: {appointment_id_str}).")
            logging.info(
                f"DEBUG: Nome do cliente capturado - Metadados: {session.get('metadata', {}).get('client_name')}, Customer Details: {session.get('customer_details', {}).get('name')}, Nome final usado: {client_name}")

            # Common purchase details for emails
            purchase_details = {
                'client_name': client_name,
                'client_email': client_email,
                'item_type': item_type,
                'purchase_date': date.today().strftime('%d/%m/%Y'),
                'purchase_time': datetime.now().time().strftime('%H:%M')
            }

            # Check if it's an 'Aula avulsa' and if appointment_id_str is a valid integer
            logging.info(
                f"DEBUG: item_type='{item_type}', appointment_id_str='{appointment_id_str}', isdigit={appointment_id_str.isdigit() if appointment_id_str else False}")

            if item_type == "Aula avulsa" and appointment_id_str and appointment_id_str.isdigit():
                logging.info(
                    f"DEBUG: Entrando no bloco de processamento de agendamento específico para ID {appointment_id_str}")
                try:
                    appointment_id_int = int(appointment_id_str)

                    # Update appointment status to paid and clear payment link
                    update_appointment_status_only(
                        db_session, appointment_id_int, AppointmentStatus.paid)
                    update_appointment_payment_link(
                        db_session, appointment_id_int, None)  # Clear link after payment
                    logging.info(
                        f"Agendamento {appointment_id_int} atualizado para status 'pago' e link de pagamento removido.")

                    # Fetch updated appointment details for email
                    appointment = get_appointment_by_id(
                        db_session, appointment_id_int)
                    if appointment:
                        # Override purchase_details with specific appointment info for emails
                        purchase_details.update({
                            'client_name': appointment.client_name,
                            'class_type': appointment.class_type,
                            'appointment_date': appointment.appointment_date.strftime('%d/%m/%Y'),
                            'appointment_time': appointment.appointment_time.strftime('%H:%M'),
                            'status': AppointmentStatus.paid.value
                        })

                        # Send confirmation email to client for appointment
                        if client_email and is_valid_email(client_email):
                            try:
                                send_email(
                                    to_email=client_email,
                                    email_type="client_confirmation",
                                    appointment_details=purchase_details,
                                    language='pt'
                                )
                                logging.info(
                                    f"Email de confirmação enviado para cliente {client_email} para agendamento {appointment_id_int}.")
                            except Exception as email_err:
                                logging.error(
                                    f"Erro ao enviar email de confirmação para o cliente {client_email} para agendamento {appointment_id_int}: {email_err}", exc_info=True)
                        else:
                            logging.warning(
                                f"Não foi possível enviar email ao cliente {client_email} para agendamento {appointment_id_int}: email inválido ou ausente.")

                        # Send notification email to company for appointment
                        if settings.YOGA_KULA_NOTIFICATION_EMAIL and is_valid_email(settings.YOGA_KULA_NOTIFICATION_EMAIL):
                            try:
                                send_email(
                                    to_email=settings.YOGA_KULA_NOTIFICATION_EMAIL,
                                    email_type="company_paid_notification",
                                    appointment_details=purchase_details,
                                    language='pt'
                                )
                                logging.info(
                                    f"Email de notificação de agendamento PAGO enviado para a empresa.")
                            except Exception as email_err:
                                logging.error(
                                    f"Erro ao enviar email de notificação PAGO para a empresa: {email_err}", exc_info=True)
                        else:
                            logging.error(
                                f"Email de notificação da empresa ({settings.YOGA_KULA_NOTIFICATION_EMAIL}) é inválido ou ausente.")

                    else:
                        logging.warning(
                            f"Agendamento com ID {appointment_id_int} não encontrado após pagamento. Emails genéricos serão enviados.")
                        # Fallback to generic emails if appointment not found, although unlikely
                        if client_email and is_valid_email(client_email):
                            try:
                                send_email(
                                    to_email=client_email,
                                    email_type="client_confirmation_generic",
                                    appointment_details=purchase_details,
                                    language='pt'
                                )
                                logging.info(
                                    f"Email genérico de pagamento enviado para cliente {client_email}.")
                            except Exception as email_err:
                                logging.error(
                                    f"Erro ao enviar email genérico de pagamento para o cliente {client_email}: {email_err}", exc_info=True)
                        else:
                            logging.warning(
                                f"Não foi possível enviar email genérico de pagamento ao cliente {client_email}: email inválido ou ausente.")

                        if settings.YOGA_KULA_NOTIFICATION_EMAIL and is_valid_email(settings.YOGA_KULA_NOTIFICATION_EMAIL):
                            try:
                                send_email(
                                    to_email=settings.YOGA_KULA_NOTIFICATION_EMAIL,
                                    email_type="company_paid_notification_generic",
                                    appointment_details=purchase_details,
                                    language='pt'
                                )
                                logging.info(
                                    f"Email genérico de pagamento enviado para a empresa.")
                            except Exception as email_err:
                                logging.error(
                                    f"Erro ao enviar email genérico de pagamento para a empresa: {email_err}", exc_info=True)
                        else:
                            logging.error(
                                f"Email de notificação da empresa ({settings.YOGA_KULA_NOTIFICATION_EMAIL}) é inválido ou ausente.")

                except ValueError:
                    logging.error(
                        f"Erro: appointment_id '{appointment_id_str}' para 'Aula avulsa' não é um número válido. Emails genéricos de compra serão enviados.")
                    # If conversion fails for 'Aula avulsa', treat as generic purchase for email purposes
                    if client_email and is_valid_email(client_email):
                        try:
                            send_email(
                                to_email=client_email,
                                email_type="client_confirmation_generic",
                                appointment_details=purchase_details,
                                language='pt'
                            )
                            logging.info(
                                f"Email genérico de pagamento enviado para cliente {client_email} (ID inválido).")
                        except Exception as email_err:
                            logging.error(
                                f"Erro ao enviar email genérico de pagamento para o cliente {client_email} (ID inválido): {email_err}", exc_info=True)
                    else:
                        logging.warning(
                            f"Não foi possível enviar email genérico de pagamento ao cliente {client_email} (ID inválido): email inválido ou ausente.")

                    if settings.YOGA_KULA_NOTIFICATION_EMAIL and is_valid_email(settings.YOGA_KULA_NOTIFICATION_EMAIL):
                        try:
                            send_email(
                                to_email=settings.YOGA_KULA_NOTIFICATION_EMAIL,
                                email_type="company_paid_notification_generic",
                                appointment_details=purchase_details,
                                language='pt'
                            )
                            logging.info(
                                f"Email genérico de pagamento enviado para a empresa (ID inválido).")
                        except Exception as email_err:
                            logging.error(
                                f"Erro ao enviar email genérico de pagamento para a empresa (ID inválido): {email_err}", exc_info=True)
                    else:
                        logging.error(
                            f"Email de notificação da empresa ({settings.YOGA_KULA_NOTIFICATION_EMAIL}) é inválido ou ausente.")

            # Handle non-appointment purchases (packs, memberships, or 'Aula avulsa' with invalid ID)
            else:
                logging.info(
                    f"Compra de '{item_type}' confirmada (não é um agendamento direto ou ID inválido).")
                # Send confirmation email for non-appointment purchases
                if client_email and is_valid_email(client_email):
                    try:
                        send_email(
                            to_email=client_email,
                            email_type="client_confirmation_generic",
                            appointment_details=purchase_details,
                            language='pt'
                        )
                        logging.info(
                            f"Emails de confirmação enviados para compra de {item_type} por {client_name}.")
                    except Exception as email_err:
                        logging.error(
                            f"Erro ao enviar email de confirmação para compra de {item_type} para o cliente {client_email}: {email_err}", exc_info=True)
                else:
                    logging.warning(
                        f"Não foi possível enviar email ao cliente {client_email} para compra de {item_type}: email inválido ou ausente.")

                if settings.YOGA_KULA_NOTIFICATION_EMAIL and is_valid_email(settings.YOGA_KULA_NOTIFICATION_EMAIL):
                    try:
                        send_email(
                            to_email=settings.YOGA_KULA_NOTIFICATION_EMAIL,
                            email_type="company_paid_notification_generic",
                            appointment_details=purchase_details,
                            language='pt'
                        )
                        logging.info(
                            f"Email de notificação para compra de {item_type} enviado para a empresa.")
                    except Exception as email_err:
                        logging.error(
                            f"Erro ao enviar email de notificação para compra de {item_type} para a empresa: {email_err}", exc_info=True)
                else:
                    logging.error(
                        f"Email de notificação da empresa ({settings.YOGA_KULA_NOTIFICATION_EMAIL}) é inválido ou ausente.")

        elif event['type'] == 'payment_intent.succeeded':
            logging.info(
                f"Payment Intent Succeeded: {event['data']['object']['id']}")
        else:
            logging.info(f"Evento Stripe não tratado: {event['type']}")

    except Exception as e:
        if db_session:
            db_session.rollback()
        logging.error(
            f"Erro geral ao processar webhook Stripe para evento {event['type']}: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error during event processing'}), 500
    finally:
        if db_session:
            db_session.close()
        if db_session_generator:
            try:
                db_session_generator.close()
            except RuntimeError:
                pass  # Generator already closed or not fully iterated

    return jsonify({'status': 'success'}), 200


if __name__ == '__main__':
    from database.db_utils import create_db_and_tables
    print("Verificando/criando banco de dados e tabelas...")
    create_db_and_tables()
    print("Banco de dados e tabelas verificados/criados.")
    app.run(debug=True, host='0.0.0.0', port=5000)
