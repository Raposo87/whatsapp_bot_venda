# utils/whatsapp_sender.py

import requests
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)

def send_whatsapp_message(to_phone_number: str, message_body: str) -> bool:
    """
    Envia uma mensagem de texto simples via WhatsApp Cloud API.
    to_phone_number deve incluir o código do país (ex: +351912345678).
    """
    if not settings.WHATSAPP_CLOUD_API_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logging.error("Credenciais do WhatsApp API incompletas. Não é possível enviar mensagem.")
        return False

    # A Meta exige que o número não tenha o '+' inicial para o campo 'to'
    formatted_phone_number = to_phone_number.replace("+", "")

    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_CLOUD_API_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": formatted_phone_number,
        "type": "text",
        "text": {"body": message_body},
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status() # Lança um erro para códigos de status HTTP ruins (4xx ou 5xx)
        logging.info(f"Mensagem WhatsApp enviada com sucesso para {to_phone_number}. Resposta: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao enviar mensagem WhatsApp para {to_phone_number}: {e}. Resposta: {e.response.text if e.response else 'N/A'}")
        return False

# Exemplo de uso (pode ser removido depois de testar)
if __name__ == "__main__":
    test_phone = "+351912345678" # Substitua pelo SEU número de WhatsApp com código de país para testar
    test_message = "Olá do Yoga Kula! Esta é uma mensagem de teste do seu bot de agendamento no WhatsApp."
    print(f"Tentando enviar mensagem WhatsApp de teste para {test_phone}...")
    success = send_whatsapp_message(test_phone, test_message)
    if success:
        print("Mensagem WhatsApp de teste enviada!")
    else:
        print("Falha ao enviar mensagem WhatsApp de teste.")