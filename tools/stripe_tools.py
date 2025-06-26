# tools/stripe_tools.py

import logging
from typing import Optional
import stripe
from app.config import settings
from sqlalchemy.orm import Session
from langchain.tools import tool
from pydantic import BaseModel, Field
from utils.email_sender import send_email  # Ainda importado
from database.db_utils import get_db, get_appointment_by_id, update_appointment_payment_link
# Não precisa mais de email.mime ou smtplib aqui se email_sender.py faz o trabalho
from datetime import datetime  # Para datetime.now().date() e time()

logging.basicConfig(level=logging.INFO)

stripe.api_key = settings.STRIPE_API_KEY

# Mapeamento de tipos de item para preços (usando os IDs do config.py)
ITEM_PRICES = {
    "Aula avulsa": 1500,  # Continua usando o valor em cêntimos para o Stripe
    "Pack experiência": 3500,
    "Mensalidade Kula": 7500,
    "Mensalidade Samadhi": 6000,
    "Mensalidade Sadhana": 4500,
    "Pack família": 2250,  # Exemplo de preço
}


class StripePaymentInput(BaseModel):
    appointment_id: Optional[int] = Field(
        None, description="ID do agendamento para aula avulsa")
    item_type: Optional[str] = Field(
        None, description="Tipo de item para pack/mensalidade")
    client_name_for_pack: Optional[str] = Field(
        None, description="Nome do cliente para pack/mensalidade")
    client_phone_for_pack: Optional[str] = Field(
        None, description="Telefone do cliente para pack/mensalidade")
    client_email_for_pack: Optional[str] = Field(
        None, description="Email do cliente para pack/mensalidade")
    language: str = Field(
        "pt", description="Idioma para o e-mail de confirmação (pt, en)")


@tool(args_schema=StripePaymentInput)
def create_stripe_payment_link(
    appointment_id: Optional[int] = None,
    item_type: Optional[str] = None,  # Tipo de item para packs/mensalidades
    client_name_for_pack: Optional[str] = None,
    client_phone_for_pack: Optional[str] = None,
    client_email_for_pack: Optional[str] = None,
    language: str = 'pt'
) -> str:
    """
    Cria um link de pagamento Stripe para uma aula avulsa, pack ou mensalidade.
    Retorna o URL do link de pagamento.
    """
    item_name = ""
    item_price = 0

    # Determinar o nome e preço do item
    if appointment_id:
        db_session = next(get_db())
        appointment = get_appointment_by_id(db_session, appointment_id)
        db_session.close()
        if appointment:
            item_name = appointment.class_type
            # Preço fixo para aula avulsa
            item_price = ITEM_PRICES.get("Aula avulsa")
            if not item_price:
                logging.error(
                    f"Preço para 'Aula avulsa' não encontrado no ITEM_PRICES.")
                return "Erro: Preço da aula avulsa não configurado."
        else:
            return "Erro: Agendamento não encontrado para criar link de pagamento."
    elif item_type and item_type in ITEM_PRICES:
        item_name = item_type
        item_price = ITEM_PRICES.get(item_type)
    else:
        return "Tipo de item inválido ou não suportado para pagamento."

    # Obter detalhes do cliente para Stripe metadata e email inicial
    customer_email_to_use = None
    current_appointment_details = {}  # Para o email inicial com o link

    if appointment_id:
        db_session = next(get_db())
        appointment = get_appointment_by_id(db_session, appointment_id)
        if appointment:
            customer_email_to_use = appointment.client_email
            current_appointment_details = {
                'client_name': appointment.client_name,
                'class_type': appointment.class_type,
                'appointment_date': appointment.appointment_date,
                'appointment_time': appointment.appointment_time,
                'client_phone': appointment.client_phone,
                'client_email': appointment.client_email
            }
        db_session.close()
    elif client_email_for_pack:  # Para packs/mensalidades diretas
        customer_email_to_use = client_email_for_pack
        current_appointment_details = {
            'client_name': client_name_for_pack,
            'class_type': item_type,  # Usar item_type para o nome da "aula" para packs
            'client_phone': client_phone_for_pack,
            'client_email': client_email_for_pack
        }

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': item_name,
                        },
                        'unit_amount': item_price,
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=settings.STRIPE_SUCCESS_URL +
            f"?session_id={{CHECKOUT_SESSION_ID}}&appointment_id={appointment_id if appointment_id else ''}",
            cancel_url=settings.STRIPE_CANCEL_URL,
            metadata={
                'appointment_id': str(appointment_id) if appointment_id else 'N/A',
                'item_type': item_type if item_type else 'Aula Avulsa',
                'client_email': customer_email_to_use,
                'client_name': current_appointment_details.get('client_name', 'N/A'),
                'client_phone': current_appointment_details.get('client_phone', 'N/A')
            },
            customer_email=customer_email_to_use,
            customer_details={
                'name': current_appointment_details.get('client_name', 'Cliente'),
                'email': customer_email_to_use
            } if current_appointment_details.get('client_name') else None,
        )
        payment_link = checkout_session.url

        # NENHUM EMAIL PARA A EMPRESA É ENVIADO AQUI.
        # A empresa só receberá a confirmação APÓS o pagamento ser confirmado via Stripe Webhook.

        # Atualizar banco de dados com o link de pagamento (para referência)
        if appointment_id:
            db_session = next(get_db())
            update_appointment_payment_link(
                db_session, appointment_id, payment_link)
            db_session.close()

        return payment_link

    except stripe.error.StripeError as e:
        logging.error(
            f"Erro no Stripe ao gerar link de pagamento: {e}", exc_info=True)
        return f"Erro no Stripe: {e.user_message if e.user_message else str(e)}. Por favor, entre em contato com o estúdio."
    except Exception as e:
        logging.error(
            f"Erro inesperado ao gerar link de pagamento: {e}", exc_info=True)
        return f"Houve um erro ao gerar o link de pagamento. Por favor, entre em contato diretamente com o estúdio pelo email {settings.YOGA_KULA_NOTIFICATION_EMAIL} ou pelo telefone +351 933782610 para concluir o pagamento e confirmar sua aula. Desculpe pelo inconveniente!"
