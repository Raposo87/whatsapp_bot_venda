# utils/whatsapp_sender.py
import requests
import logging
import os
from app.config import settings # Importa o objeto settings (necessário para pegar tokens e IDs)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def send_whatsapp_message(to_number: str, message_body: str):
    """
    Envia uma mensagem de texto via WhatsApp Cloud API.

    Args:
        to_number (str): O número de telefone do destinatário (incluindo código do país).
        message_body (str): O conteúdo da mensagem de texto a ser enviada.
    """
    # URL da API do WhatsApp Cloud
    # Assegure que settings.WHATSAPP_PHONE_NUMBER_ID está configurado no seu .env
    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    # Cabeçalhos da requisição
    # Assegure que settings.WHATSAPP_CLOUD_API_TOKEN está configurado no seu .env
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_CLOUD_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Dados da mensagem no formato JSON exigido pela API
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,  # O nome do parâmetro 'to' é o que a API do WhatsApp espera
        "type": "text",
        "text": {
            "body": message_body # O nome do parâmetro 'body' é o que a API do WhatsApp espera para texto
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status() # Levanta um HTTPError para respostas de erro (4xx ou 5xx)
        logging.info(f"Mensagem WhatsApp enviada com sucesso para {to_number}.")
        logging.debug(f"Resposta da API do WhatsApp: {response.json()}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao enviar mensagem WhatsApp para {to_number}: {e}", exc_info=True)
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Resposta de erro da API do WhatsApp: {e.response.text}")
        raise # Re-lança a exceção para ser tratada no chamador (whatsapp_api.py)