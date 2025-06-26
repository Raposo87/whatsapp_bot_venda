# utils/email_sender.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
import logging
from typing import Optional
from datetime import datetime, date, time
from email.utils import formataddr

logging.basicConfig(level=logging.INFO)

# --- Adicionando traduções para os e-mails ---
EMAIL_SUBJECTS = {
    'company_pending_notification': {
        'pt': 'NOVO AGENDAMENTO (Pendente Pagamento) - Yoga Kula',
        'en': 'NEW APPOINTMENT (Payment Pending) - Yoga Kula'
    },
    'client_confirmation': {
        'pt': 'Confirmação de Agendamento e Pagamento - Yoga Kula',
        'en': 'Appointment & Payment Confirmed - Yoga Kula'
    },
    'client_confirmation_generic': {
        'pt': 'Confirmação de Pagamento - Yoga Kula',
        'en': 'Payment Confirmation - Yoga Kula'
    },
    'company_paid_notification': {
        'pt': 'CONFIRMAÇÃO: Novo Agendamento Pago - Yoga Kula',
        'en': 'CONFIRMED: New Paid Appointment - Yoga Kula'
    },
    'company_paid_notification_generic': {
        'pt': 'CONFIRMAÇÃO: Novo Pagamento Processado - Yoga Kula',
        'en': 'CONFIRMED: New Payment Processed - Yoga Kula'
    },
    'whatsapp_verification': {
        'pt': 'Código de Verificação WhatsApp - Yoga Kula',
        'en': 'WhatsApp Verification Code - Yoga Kula'
    },
    'password_reset': {
        'pt': 'Redefinição de Senha - Yoga Kula',
        'en': 'Password Reset - Yoga Kula'
    },
}

EMAIL_TEMPLATES = {
    'company_pending_notification': {
        'pt': """
Novo agendamento PENDENTE DE PAGAMENTO no Yoga Kula!

Detalhes do Agendamento:
Nome do Cliente: {client_name}
Telefone: {client_phone}
Email: {client_email}
Tipo de Aula: {class_type}
Data: {appointment_date}
Hora: {appointment_time}

Status: Pendente de Pagamento

Por favor, verifique o status do pagamento.
""",
        'en': """
New APPOINTMENT PENDING PAYMENT at Yoga Kula!

Appointment Details:
Client Name: {client_name}
Phone: {client_phone}
Email: {client_email}
Class Type: {class_type}
Date: {appointment_date}
Time: {appointment_time}

Status: Payment Pending

Please check the payment status.
"""
    },
    'client_confirmation': {
        'pt': """
🌟 Olá {client_name}! 🌟

🎉 PARABÉNS! O seu pagamento foi confirmado com sucesso! 🎉

✨ A sua aula de {class_type} no Yoga Kula está oficialmente agendada para:
📅 Data: {appointment_date}
⏰ Hora: {appointment_time} (hora de Lisboa)

🧘‍♀️ Prepare-se para uma experiência incrível de yoga! 

📋 Lembre-se de trazer:
• Roupa confortável
• Tapete de yoga (se tiver)
• Água
• Boa disposição! 😊

📍 Localização: Yoga Kula Studio
🅿️ Estacionamento disponível

📞 Se precisar de alguma coisa, não hesite em contactar-nos!

Mal podemos esperar para o/a receber e partilhar esta jornada de bem-estar consigo! 

Namastê 🙏
A Equipa Yoga Kula
""",
        'en': """
🌟 Hello {client_name}! 🌟

🎉 CONGRATULATIONS! Your payment has been successfully confirmed! 🎉

✨ Your {class_type} class at Yoga Kula is officially scheduled for:
📅 Date: {appointment_date}
⏰ Time: {appointment_time} (Lisbon time)

🧘‍♀️ Get ready for an amazing yoga experience!

📋 Remember to bring:
• Comfortable clothing
• Yoga mat (if you have one)
• Water
• Good vibes! 😊

📍 Location: Yoga Kula Studio
🅿️ Parking available

📞 If you need anything, don't hesitate to contact us!

We can't wait to welcome you and share this wellness journey with you!

Namaste 🙏
The Yoga Kula Team
"""
    },
    'client_confirmation_generic': {
        'pt': """
🌟 Olá {client_name}! 🌟

🎉 PARABÉNS! O seu pagamento foi confirmado com sucesso! 🎉

✨ Obrigado por escolher o Yoga Kula para a sua jornada de bem-estar!

🧘‍♀️ A sua compra de {item_type} foi processada com êxito.

📅 Data do Pagamento: {purchase_date}
⏰ Hora do Pagamento: {purchase_time}

📞 Se tiver alguma dúvida sobre a sua compra, não hesite em contactar-nos!

Mal podemos esperar para o/a receber no nosso estúdio e partilhar esta jornada de yoga consigo!

Namastê 🙏
A Equipa Yoga Kula
""",
        'en': """
🌟 Hello {client_name}! 🌟

🎉 CONGRATULATIONS! Your payment has been successfully confirmed! 🎉

✨ Thank you for choosing Yoga Kula for your wellness journey!

🧘‍♀️ Your purchase of {item_type} has been processed successfully.

📅 Payment Date: {purchase_date}
⏰ Payment Time: {purchase_time}

📞 If you have any questions about your purchase, don't hesitate to contact us!

We can't wait to welcome you to our studio and share this yoga journey with you!

Namaste 🙏
The Yoga Kula Team
"""
    },
    'company_paid_notification': {
        'pt': """
CONFIRMADO: Novo Agendamento PAGO no Yoga Kula!

Detalhes do Agendamento:
Nome do Cliente: {client_name}
Email: {client_email}
Tipo de Aula: {class_type}
Data: {appointment_date}
Hora: {appointment_time}

Status: Pagamento Confirmado

O pagamento para este agendamento foi processado com sucesso.
""",
        'en': """
CONFIRMED: New PAID Appointment at Yoga Kula!

Appointment Details:
Client Name: {client_name}
Email: {client_email}
Class Type: {class_type}
Date: {appointment_date}
Time: {appointment_time}

Status: Payment Confirmed

The payment for this appointment has been successfully processed.
"""
    },
    'company_paid_notification_generic': {
        'pt': """
CONFIRMADO: Novo Pagamento Processado no Yoga Kula!

Detalhes do Pagamento:
Nome do Cliente: {client_name}
Email: {client_email}
Tipo de Item: {item_type}
Data do Pagamento: {purchase_date}
Hora do Pagamento: {purchase_time}

Status: Pagamento Confirmado

O pagamento foi processado com sucesso.
""",
        'en': """
CONFIRMED: New Payment Processed at Yoga Kula!

Payment Details:
Client Name: {client_name}
Email: {client_email}
Item Type: {item_type}
Payment Date: {purchase_date}
Payment Time: {purchase_time}

Status: Payment Confirmed

The payment has been successfully processed.
"""
    },
    'whatsapp_verification': {
        'pt': """
Olá,

O seu código de verificação para o WhatsApp do Yoga Kula é: {verification_code}.
Este código é válido por {validity_minutes} minutos.

Por favor, insira este código no chat para completar a verificação.
""",
        'en': """
Hello,

Your verification code for Yoga Kula's WhatsApp is: {verification_code}.
This code is valid for {validity_minutes} minutes.

Please enter this code in the chat to complete the verification.
"""
    },
    'password_reset': {
        'pt': """
Olá {client_name},

Recebemos um pedido para redefinir a sua senha.
Por favor, clique no link abaixo para criar uma nova senha:

{reset_link}

Se não solicitou esta redefinição, por favor ignore este email.

Atenciosamente,
A Equipa Yoga Kula
""",
        'en': """
Hello {client_name},

We received a request to reset your password.
Please click the link below to create a new password:

{reset_link}

If you did not request a password reset, please ignore this email.

Sincerely,
The Yoga Kula Team
"""
    },
}


def send_email(
    to_email: str,
    email_type: str,
    appointment_details: dict,
    reset_link: Optional[str] = None,
    language: str = 'pt'  # Default language is Portuguese
):
    """
    Sends an email using the provided details.

    Args:
        to_email (str): Recipient's email address.
        email_type (str): Type of email (e.g., 'client_confirmation', 'company_notification', 'company_pending_notification').
        appointment_details (dict): Dictionary with details for the email content (e.g., client_name, class_type, appointment_date, appointment_time, client_phone, client_email).
        reset_link (Optional[str]): The password reset link, if applicable.
        language (str): Language for the email content ('pt' for Portuguese, 'en' for English).
    """

    if not settings.EMAIL_HOST or not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        logging.error(
            "Configurações de e-mail incompletas. Verifique as variáveis de ambiente EMAIL_HOST, EMAIL_HOST_USER e EMAIL_HOST_PASSWORD.")
        return

    # Ensure language is one of the supported ones
    if language not in ['pt', 'en']:
        logging.warning(
            f"Idioma '{language}' não suportado para e-mail. Usando 'pt' como padrão.")
        language = 'pt'

    subject = EMAIL_SUBJECTS.get(email_type, {}).get(
        language, 'Assunto Padrão - Yoga Kula')
    template = EMAIL_TEMPLATES.get(email_type, {}).get(language)

    if not template:
        logging.error(
            f"Template de e-mail para '{email_type}' no idioma '{language}' não encontrado.")
        return

    # Prepare data for template formatting, converting date/time objects to strings
    formatted_details = appointment_details.copy()
    if 'appointment_date' in formatted_details and isinstance(formatted_details['appointment_date'], (date, datetime)):
        formatted_details['appointment_date'] = formatted_details['appointment_date'].strftime(
            '%d-%m-%Y')
    if 'appointment_time' in formatted_details and isinstance(formatted_details['appointment_time'], (time, datetime)):
        formatted_details['appointment_time'] = formatted_details['appointment_time'].strftime(
            '%H:%M')

    # Add reset_link to formatted_details if it exists
    if reset_link:
        formatted_details['reset_link'] = reset_link
    if 'validity_minutes' not in formatted_details and email_type == 'whatsapp_verification':
        # Default for verification if not provided
        formatted_details['validity_minutes'] = 10

    try:
        body = template.format(**formatted_details)
    except KeyError as e:
        logging.error(
            f"Erro de formatação no template do email '{email_type}' para o idioma '{language}': Chave ausente - {e}. Detalhes disponíveis: {formatted_details.keys()}")
        return
    except Exception as e:
        logging.error(
            f"Erro inesperado ao formatar o template do email '{email_type}': {e}", exc_info=True)
        return

    msg = MIMEMultipart()
    msg['From'] = formataddr(('Yoga Kula Studio', settings.EMAIL_HOST_USER))
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # ALTERAÇÃO CRÍTICA AQUI: Usar smtplib.SMTP e starttls()
        # Conecta ao servidor SMTP (geralmente porta 587 para STARTTLS)
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.ehlo()  # Pode ser necessário para alguns servidores
            server.starttls()  # Inicia a criptografia TLS
            server.ehlo()  # Pode ser necessário novamente após STARTTLS
            server.login(settings.EMAIL_HOST_USER,
                         settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.EMAIL_HOST_USER,
                            to_email, msg.as_string())
        logging.info(
            f"Email '{email_type}' enviado com sucesso para {to_email}.")
    except smtplib.SMTPException as e:
        logging.error(
            f"Falha no envio do email '{email_type}' para {to_email}: {e}")
    except Exception as e:
        logging.error(
            f"Erro inesperado ao enviar email '{email_type}' para {to_email}: {e}", exc_info=True)


if __name__ == '__main__':
    # Apenas para testes locais
    # Certifique-se de que as variáveis de ambiente no .env estão configuradas para o envio de e-mails de teste
    # Ex: EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD

    test_email = os.getenv("TEST_EMAIL_RECIPIENT",
                           "seu.email.de.teste@exemplo.com")

    # Exemplo de uso para cliente (notificação de agendamento pendente)
    test_details_pending_notification = {
        'client_name': 'Igor Raposo',
        'class_type': 'Meditação',
        'appointment_date': date(2025, 7, 23),
        'appointment_time': time(14, 0),
        'client_phone': '+351912345678',
        'client_email': 'igorraposo02@gmail.com',
    }
    print("Tentando enviar e-mail de NOTIFICAÇÃO DE AGENDAMENTO PENDENTE em Português...")
    send_email(
        to_email=test_email,
        email_type="company_pending_notification",
        appointment_details=test_details_pending_notification,
        language='pt'
    )
    print("\nTentando enviar e-mail de NOTIFICAÇÃO DE AGENDAMENTO PENDENTE em Inglês...")
    send_email(
        to_email=test_email,
        email_type="company_pending_notification",
        appointment_details=test_details_pending_notification,
        language='en'
    )

    # Exemplo de uso para notificação da empresa (pendente de pagamento)
    test_details_company_pending = {
        'client_name': 'Igor Raposo',
        'client_phone': '+351912345678',
        'client_email': 'igorraposo02@gmail.com',
        'class_type': 'Vinyasa Yoga',
        'appointment_date': date(2025, 7, 24),
        'appointment_time': time(10, 30),
    }
    print("\nTentando enviar e-mail de NOTIFICAÇÃO DA EMPRESA (PENDENTE) em Português...")
    send_email(
        to_email=settings.YOGA_KULA_NOTIFICATION_EMAIL,
        email_type="company_pending_notification",
        appointment_details=test_details_company_pending,
        language='pt'
    )

    # Exemplo de uso para confirmação de pagamento do cliente
    test_details_client_confirmed = {
        'client_name': 'Maria Silva',
        'class_type': 'Hatha Yoga',
        'appointment_date': date(2025, 7, 25),
        'appointment_time': time(9, 0),
    }
    print("\nTentando enviar e-mail de CONFIRMAÇÃO DE PAGAMENTO (CLIENTE) em Português...")
    send_email(
        to_email=test_email,
        email_type="client_confirmation",
        appointment_details=test_details_client_confirmed,
        language='pt'
    )

    # Exemplo de uso para notificação da empresa (pagamento confirmado)
    test_details_company_paid = {
        'client_name': 'João Nuno',
        'client_email': 'joao.nuno@example.com',
        'class_type': 'Ashtanga Yoga',
        'appointment_date': date(2025, 7, 26),
        'appointment_time': time(18, 0),
    }
    print("\nTentando enviar e-mail de NOTIFICAÇÃO DA EMPRESA (PAGO) em Português...")
    send_email(
        to_email=settings.YOGA_KULA_NOTIFICATION_EMAIL,
        email_type="company_paid_notification",
        appointment_details=test_details_company_paid,
        language='pt'
    )

    # Exemplo de uso para verificação de WhatsApp
    test_details_whatsapp_verification = {
        'verification_code': '123456',
        'validity_minutes': 10  # Example of passing validity
    }
    print("\nTentando enviar e-mail de VERIFICAÇÃO WHATSAPP em Português...")
    send_email(
        to_email=test_email,
        email_type="whatsapp_verification",
        appointment_details=test_details_whatsapp_verification,
        language='pt'
    )

    # Exemplo de uso para redefinição de senha
    test_details_password_reset = {
        'client_name': 'Carlos Dias',
    }
    print("\nTentando enviar e-mail de REDEFINIÇÃO DE SENHA em Português...")
    send_email(
        to_email=test_email,
        email_type="password_reset",
        appointment_details=test_details_password_reset,
        reset_link="https://exemplo.com/redefinir-senha/token-aqui",
        language='pt'
    )
