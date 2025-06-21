# utils/email_sender.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
import logging
from typing import Optional
from datetime import datetime, date, time # Adicionado 'time' aqui
from email.utils import formataddr

logging.basicConfig(level=logging.INFO)

# --- Adicionando traduções para os e-mails ---
EMAIL_SUBJECTS = {
    'client_payment_link': {
        'pt': 'Confirmação de Agendamento e Link de Pagamento - Yoga Kula',
        'en': 'Appointment Confirmation & Payment Link - Yoga Kula'
    },
    'company_pending_notification': {
        'pt': 'NOVO AGENDAMENTO (Pendente Pagamento) - Yoga Kula',
        'en': 'NEW APPOINTMENT (Payment Pending) - Yoga Kula'
    },
    'client_confirmation': {
        'pt': 'Confirmação de Agendamento e Pagamento - Yoga Kula',
        'en': 'Appointment & Payment Confirmed - Yoga Kula'
    },
    'company_paid_notification': {
        'pt': 'CONFIRMAÇÃO: Novo Agendamento Pago - Yoga Kula',
        'en': 'CONFIRMED: New Paid Appointment - Yoga Kula'
    },
    'payment_link_only': { # Para o caso de enviar só o link, sem detalhes completos de agendamento inicial
        'pt': 'Seu Link de Pagamento - Yoga Kula',
        'en': 'Your Payment Link - Yoga Kula'
    },
    'whatsapp_verification': {
        'pt': 'Código de Verificação WhatsApp - Yoga Kula',
        'en': 'WhatsApp Verification Code - Yoga Kula'
    },
    'password_reset': {
        'pt': 'Redefinição de Senha - Yoga Kula',
        'en': 'Password Reset - Yoga Kula'
    }
}

EMAIL_BODIES_CLIENT_PAYMENT_LINK = {
    'pt': {
        'greeting': 'Olá {client_name},',
        'intro': 'Obrigado por agendar sua aula de {class_type} no Yoga Kula!',
        'details': 'Detalhes do agendamento:',
        'class_type_label': 'Aula:',
        'date_label': 'Data:',
        'time_label': 'Hora:',
        'phone_label': 'Telefone:',
        'email_label': 'Email:',
        'payment_info': 'Por favor, siga este link para completar o pagamento da sua aula:',
        'payment_link_text': 'Pagar Aula',
        'closing': 'Aguardamos a sua visita!',
        'signature': 'Com gratidão,<br>A Equipa Yoga Kula'
    },
    'en': {
        'greeting': 'Hello {client_name},',
        'intro': 'Thank you for booking your {class_type} class at Yoga Kula!',
        'details': 'Appointment details:',
        'class_type_label': 'Class:',
        'date_label': 'Date:',
        'time_label': 'Time:',
        'phone_label': 'Phone:',
        'email_label': 'Email:',
        'payment_info': 'Please follow this link to complete the payment for your class:',
        'payment_link_text': 'Pay for Class',
        'closing': 'We look forward to seeing you!',
        'signature': 'With gratitude,<br>The Yoga Kula Team'
    }
}

EMAIL_BODIES_COMPANY_PENDING_NOTIFICATION = {
    'pt': {
        'intro': 'Um novo agendamento foi criado e está aguardando pagamento:',
        'details': 'Detalhes do Agendamento:',
        'client_name_label': 'Cliente:',
        'class_type_label': 'Aula:',
        'date_label': 'Data:',
        'time_label': 'Hora:',
        'phone_label': 'Telefone:',
        'email_label': 'Email:',
        'status': 'Status: Pendente Pagamento',
        'payment_link_info': 'Link de Pagamento:',
        'action': 'Aguarde a confirmação de pagamento para validar o agendamento.'
    },
    'en': {
        'intro': 'A new appointment has been created and is awaiting payment:',
        'details': 'Appointment Details:',
        'client_name_label': 'Client:',
        'class_type_label': 'Class:',
        'date_label': 'Date:',
        'time_label': 'Time:',
        'phone_label': 'Phone:',
        'email_label': 'Email:',
        'status': 'Status: Payment Pending',
        'payment_link_info': 'Payment Link:',
        'action': 'Await payment confirmation to validate the booking.'
    }
}

EMAIL_BODIES_CLIENT_CONFIRMATION = {
    'pt': {
        'greeting': 'Olá {client_name},',
        'intro': 'Seu agendamento para a aula de {class_type} no Yoga Kula foi CONFIRMADO e o pagamento processado com sucesso!',
        'details': 'Detalhes do agendamento:',
        'class_type_label': 'Aula:',
        'date_label': 'Data:',
        'time_label': 'Hora:',
        'payment_status': 'Status do Pagamento: Pago',
        'closing': 'Aguardamos a sua visita!',
        'signature': 'Com gratidão,<br>A Equipa Yoga Kula'
    },
    'en': {
        'greeting': 'Hello {client_name},',
        'intro': 'Your booking for the {class_type} class at Yoga Kula has been CONFIRMED and payment successfully processed!',
        'details': 'Appointment details:',
        'class_type_label': 'Class:',
        'date_label': 'Date:',
        'time_label': 'Time:',
        'payment_status': 'Payment Status: Paid',
        'closing': 'We look forward to seeing you!',
        'signature': 'With gratitude,<br>The Yoga Kula Team'
    }
}

EMAIL_BODIES_COMPANY_PAID_NOTIFICATION = {
    'pt': {
        'intro': 'Um agendamento foi PAGO e CONFIRMADO:',
        'details': 'Detalhes do Agendamento:',
        'client_name_label': 'Cliente:',
        'class_type_label': 'Aula:',
        'date_label': 'Data:',
        'time_label': 'Hora:',
        'phone_label': 'Telefone:',
        'email_label': 'Email:',
        'status': 'Status: Pago e Confirmado',
        'payment_link_info': 'Link de Pagamento:',
        'action': 'O agendamento está validado.'
    },
    'en': {
        'intro': 'An appointment has been PAID and CONFIRMED:',
        'details': 'Appointment Details:',
        'client_name_label': 'Client:',
        'class_type_label': 'Class:',
        'date_label': 'Date:',
        'time_label': 'Time:',
        'phone_label': 'Phone:',
        'email_label': 'Email:',
        'status': 'Status: Paid & Confirmed',
        'payment_link_info': 'Payment Link:',
        'action': 'The booking is validated.'
    }
}

EMAIL_BODIES_PAYMENT_LINK_ONLY = {
    'pt': {
        'greeting': 'Olá {client_name},',
        'intro': 'Aqui está o link de pagamento solicitado:',
        'payment_info': 'Pague aqui:',
        'payment_link_text': 'Acessar Link de Pagamento',
        'closing': 'Qualquer dúvida, estamos à disposição!',
        'signature': 'Com gratidão,<br>A Equipa Yoga Kula'
    },
    'en': {
        'greeting': 'Hello {client_name},',
        'intro': 'Here is your requested payment link:',
        'payment_info': 'Pay here:',
        'payment_link_text': 'Access Payment Link',
        'closing': 'If you have any questions, feel free to contact us!',
        'signature': 'With gratitude,<br>The Yoga Kula Team'
    }
}

# Novo tipo de e-mail para verificação do WhatsApp
EMAIL_BODIES_WHATSAPP_VERIFICATION = {
    'pt': {
        'greeting': 'Olá,',
        'intro': 'Aqui está o seu código de verificação para o WhatsApp Business API do Yoga Kula:',
        'code_label': 'Código de Verificação:',
        'closing': 'Use este código para confirmar seu número no WhatsApp.',
        'signature': 'Com gratidão,<br>A Equipa Yoga Kula'
    },
    'en': {
        'greeting': 'Hello,',
        'intro': 'Here is your verification code for Yoga Kula\'s WhatsApp Business API:',
        'code_label': 'Verification Code:',
        'closing': 'Use this code to confirm your number on WhatsApp.',
        'signature': 'With gratitude,<br>The Yoga Kula Team'
    }
}

# Novo tipo de e-mail para redefinição de senha (se aplicável)
EMAIL_BODIES_PASSWORD_RESET = {
    'pt': {
        'greeting': 'Olá {client_name},',
        'intro': 'Você solicitou a redefinição da sua senha. Clique no link abaixo para redefini-la:',
        'reset_link_text': 'Redefinir Senha',
        'closing': 'Se você não solicitou isso, por favor, ignore este e-mail.',
        'signature': 'Com gratidão,<br>A Equipa Yoga Kula'
    },
    'en': {
        'greeting': 'Hello {client_name},',
        'intro': 'You requested a password reset. Click the link below to reset it:',
        'reset_link_text': 'Reset Password',
        'closing': 'If you did not request this, please ignore this email.',
        'signature': 'With gratitude,<br>The Yoga Kula Team'
    }
}


# Mapeamento de email_type para os corpos de e-mail
EMAIL_BODY_MAP = {
    'client_payment_link': EMAIL_BODIES_CLIENT_PAYMENT_LINK,
    'company_pending_notification': EMAIL_BODIES_COMPANY_PENDING_NOTIFICATION,
    'client_confirmation': EMAIL_BODIES_CLIENT_CONFIRMATION,
    'company_paid_notification': EMAIL_BODIES_COMPANY_PAID_NOTIFICATION,
    'payment_link_only': EMAIL_BODIES_PAYMENT_LINK_ONLY,
    'whatsapp_verification': EMAIL_BODIES_WHATSAPP_VERIFICATION,
    'password_reset': EMAIL_BODIES_PASSWORD_RESET
}

def send_email(
    to_email: str,
    email_type: str, # Novo parâmetro para indicar o tipo de e-mail
    appointment_details: dict,
    payment_link: Optional[str] = None,
    language: str = 'pt'
) -> bool:
    """
    Envia e-mails com base em um tipo predefinido, buscando o assunto e o corpo
    dos dicionários EMAIL_SUBJECTS e EMAIL_BODY_MAP.

    Args:
        to_email (str): O endereço de e-mail do destinatário.
        email_type (str): O tipo de e-mail a ser enviado (ex: 'client_payment_link', 'company_pending_notification', etc.).
        appointment_details (dict): Dicionário com os detalhes do agendamento/cliente.
        payment_link (Optional[str]): Link de pagamento (opcional, usado para e-mails de pagamento).
        language (str): Idioma do e-mail ('pt' ou 'en').
    """
    lang_code = language if language in ['pt', 'en'] else 'pt'

    subject = EMAIL_SUBJECTS.get(email_type, {}).get(lang_code, 'Assunto Padrão')
    email_body_template = EMAIL_BODY_MAP.get(email_type, {}).get(lang_code, {})

    if not email_body_template:
        logging.error(f"Modelo de e-mail para o tipo '{email_type}' no idioma '{lang_code}' não encontrado.")
        return False

    # Formatar o corpo do e-mail
    body_parts = []
    # Saudações e introdução
    if 'greeting' in email_body_template:
        body_parts.append(email_body_template['greeting'].format(**appointment_details))
    if 'intro' in email_body_template:
        body_parts.append(email_body_template['intro'].format(**appointment_details))

    # Detalhes do agendamento (se aplicável)
    if 'details' in email_body_template and email_type in ['client_payment_link', 'company_pending_notification', 'client_confirmation', 'company_paid_notification']:
        body_parts.append(f"<p><strong>{email_body_template['details']}</strong></p>")
        if 'class_type_label' in email_body_template and 'class_type' in appointment_details:
            body_parts.append(f"<p>{email_body_template['class_type_label']} {appointment_details['class_type']}</p>")
        if 'appointment_date_label' in email_body_template and 'appointment_date' in appointment_details: # Adicionado
            body_parts.append(f"<p>{email_body_template['appointment_date_label']} {appointment_details['appointment_date'].strftime('%d-%m-%Y')}</p>")
        elif 'date_label' in email_body_template and 'appointment_date' in appointment_details:
             body_parts.append(f"<p>{email_body_template['date_label']} {appointment_details['appointment_date'].strftime('%d-%m-%Y')}</p>")

        if 'appointment_time_label' in email_body_template and 'appointment_time' in appointment_details: # Adicionado
            body_parts.append(f"<p>{email_body_template['appointment_time_label']} {appointment_details['appointment_time'].strftime('%H:%M')}</p>")
        elif 'time_label' in email_body_template and 'appointment_time' in appointment_details:
            body_parts.append(f"<p>{email_body_template['time_label']} {appointment_details['appointment_time'].strftime('%H:%M')}</p>")

        if 'client_name_label' in email_body_template and 'client_name' in appointment_details: # Adicionado para empresa
            body_parts.append(f"<p>{email_body_template['client_name_label']} {appointment_details['client_name']}</p>")
        if 'phone_label' in email_body_template and 'client_phone' in appointment_details:
            body_parts.append(f"<p>{email_body_template['phone_label']} {appointment_details['client_phone']}</p>")
        if 'email_label' in email_body_template and 'client_email' in appointment_details:
            body_parts.append(f"<p>{email_body_template['email_label']} {appointment_details['client_email']}</p>")
        if 'status' in email_body_template: # Adicionado para empresa
            body_parts.append(f"<p>{email_body_template['status']}</p>")
        if 'action' in email_body_template: # Adicionado para empresa
            body_parts.append(f"<p>{email_body_template['action']}</p>")


    # Link de pagamento (se aplicável)
    if payment_link and 'payment_info' in email_body_template:
        body_parts.append(f"<p>{email_body_template['payment_info']}</p>")
        body_parts.append(f"<p><a href=\"{payment_link}\">{email_body_template['payment_link_text']}</a></p>")
    elif payment_link and 'reset_link_text' in email_body_template and email_type == 'password_reset':
        body_parts.append(f"<p><a href=\"{payment_link}\">{email_body_template['reset_link_text']}</a></p>")


    # Código de verificação (para WhatsApp, se aplicável)
    if email_type == 'whatsapp_verification' and 'verification_code' in appointment_details:
        body_parts.append(f"<p>{email_body_template['code_label']} <strong>{appointment_details['verification_code']}</strong></p>")

    # Fechamento e Assinatura
    if 'closing' in email_body_template:
        body_parts.append(f"<p>{email_body_template['closing']}</p>")
    if 'signature' in email_body_template:
        body_parts.append(f"<p>{email_body_template['signature']}</p>")

    body = "<br>".join(body_parts)

    msg = MIMEMultipart("alternative")
    msg['From'] = formataddr(('Yoga Kula', settings.EMAIL_SENDER)) # Exibe 'Yoga Kula' como remetente
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)
        logging.info(f"E-mail enviado com sucesso para {to_email} ({email_type}) no idioma {lang_code}") # Atualizado log
        return True
    except Exception as e:
        logging.error(f"Erro ao enviar e-mail para {to_email} ({email_type}): {e}") # Atualizado log
        return False

# Exemplo de uso
if __name__ == "__main__":
    from datetime import datetime, date, time
    test_email = "seu.email@exemplo.com" # Mude para um e-mail real para testar

    # Exemplo de uso em Português - Link de Pagamento Cliente
    test_details_client_payment_link = {
        'client_name': 'João Silva',
        'class_type': 'Hatha Yoga',
        'appointment_date': date(2025, 7, 10),
        'appointment_time': time(18, 0),
        'client_phone': '+351912345678',
        'client_email': 'joao@exemplo.com'
    }
    test_payment_link = "https://exemplo.com/pagamento"
    print("\nTentando enviar e-mail de link de pagamento CLIENTE em Português...")
    send_email(
        to_email=test_email,
        email_type="client_payment_link",
        appointment_details=test_details_client_payment_link,
        payment_link=test_payment_link,
        language='pt'
    )

    # Exemplo de uso em Português - Notificação Pendente Empresa
    test_details_company_pending = {
        'client_name': 'Maria Oliveira',
        'class_type': 'Vinyasa Yoga',
        'appointment_date': date(2025, 7, 11),
        'appointment_time': time(9, 30),
        'client_phone': '+351923456789',
        'client_email': 'maria@exemplo.com'
    }
    print("\nTentando enviar e-mail de notificação PENDENTE EMPRESA em Português...")
    send_email(
        to_email="geral.kulayogastudio@gmail.com",
        email_type="company_pending_notification",
        appointment_details=test_details_company_pending,
        payment_link="https://exemplo.com/link-pagamento-empresa", # Link pode ser o mesmo ou não
        language='pt'
    )

    # Exemplo de uso em Português - Confirmação Cliente (PAGO)
    test_details_client_confirm = {
        'client_name': 'João Silva',
        'class_type': 'Hatha Yoga',
        'appointment_date': date(2025, 7, 10),
        'appointment_time': time(18, 0)
    }
    print("\nTentando enviar e-mail de CONFIRMAÇÃO CLIENTE (PAGO) em Português...")
    send_email(
        to_email=test_email,
        email_type="client_confirmation",
        appointment_details=test_details_client_confirm,
        language='pt'
    )

    # Exemplo de uso em Português - Confirmação Empresa (PAGO)
    test_details_company_confirm = {
        'client_name': 'João Silva',
        'class_type': 'Hatha Yoga',
        'appointment_date': date(2025, 7, 10),
        'appointment_time': time(18, 0),
        'client_phone': '+351912345678',
        'client_email': 'joao@exemplo.com'
    }
    print("\nTentando enviar e-mail de CONFIRMAÇÃO EMPRESA (PAGO) em Português...")
    send_email(
        to_email="geral.kulayogastudio@gmail.com",
        email_type="company_paid_notification",
        appointment_details=test_details_company_confirm,
        payment_link="https://exemplo.com/link-pagamento-pago-empresa", # Opcional, pode ser o mesmo
        language='pt'
    )

    # Exemplo de uso para enviar apenas link de pagamento (para packs/mensalidades)
    test_details_payment_only = {
        'client_name': 'Ana Costa',
    }
    print("\nTentando enviar e-mail de LINK DE PAGAMENTO APENAS em Português...")
    send_email(
        to_email=test_email,
        email_type="payment_link_only",
        appointment_details=test_details_payment_only,
        payment_link="https://exemplo.com/link-pack-mensalidade",
        language='pt'
    )

    # Exemplo de uso para verificação de WhatsApp
    test_details_whatsapp_verification = {
        'verification_code': '123456',
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
        payment_link="https://exemplo.com/reset-password", # O link de redefinição de senha
        language='pt'
    )