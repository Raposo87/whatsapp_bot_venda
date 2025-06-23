# config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

    STRIPE_API_KEY: str = os.getenv("STRIPE_API_KEY")

    # NOVAS CONFIGURAÇÕES STRIPE - AJUSTADAS PARA MELHOR FLEXIBILIDADE
    # Estes devem ser definidos no seu .env para a URL real do seu frontend
    STRIPE_SUCCESS_URL: str = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/success") # Ajustado para um localhost comum, altere no .env!
    STRIPE_CANCEL_URL: str = os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/cancel")   # Ajustado, altere no .env!
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET") # Adicionado

    YOGA_KULA_NOTIFICATION_EMAIL: str = os.getenv("YOGA_KULA_NOTIFICATION_EMAIL", "geral.kulayogastudio@gmail.com")

    # Credenciais de Email
    EMAIL_HOST: str = os.getenv("EMAIL_HOST")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_HOST_USER: str = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD: str = os.getenv("EMAIL_HOST_PASSWORD")
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER")

    # Credenciais WhatsApp Business API
    WHATSAPP_CLOUD_API_TOKEN: str = os.getenv("WHATSAPP_CLOUD_API_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN")

    # CONFIGURAÇÕES DO STRIPE PRICE IDs
    STRIPE_PRICE_IDS: dict = {
        "Hatha Yoga (Nível Iniciante e Intermédio)": os.getenv("STRIPE_PRICE_ID_AULA_HATHA_YOGA(NÍVEL_INICIANTE_INTERMÉDIO)", "price_1RbRtVRGn5VRPX0Um3Jt834W"),
        "Vinyasa Yoga (Nível Intermédio)": os.getenv("STRIPE_PRICE_ID_AULA_VINYASA_YOGA(NÍVEL_INTERMÉDIO)", "price_1RbRtVRGn5VRPX0Um3Jt834W"),
        "Yoga Suave (Nível Iniciante)": os.getenv("STRIPE_PRICE_ID_AULA_YOGA_SUAVE(NÍVEL_INICIANTE)", "price_1RbRtVRGn5VRPX0Um3Jt834W"),
        "Yoga Aéreo (Nível Iniciante e Intermédio)": os.getenv("STRIPE_PRICE_ID_AULA_YOGA_AÉREO(NÍVEL_INICIANTE_INTERMÉDIO)", "price_1RbRtVRGn5VRPX0Um3Jt834W"),
        "Yoga Dinâmico (Nível Variável)": os.getenv("STRIPE_PRICE_ID_AULA_YOGA_DINÂMICO(NÍVEL_VARIÁVEL)", "price_1RbRtVRGn5VRPX0Um3Jt834W"),
        "Meditação": os.getenv("STRIPE_PRICE_ID_AULA_MEDITAÇÃO", "price_1RbRtVRGn5VRPX0Um3Jt834W"),
        "Aula avulsa": os.getenv("STRIPE_PRICE_ID_AULA_AVULSA", "price_1RbRtVRGn5VRPX0Um3Jt834W"),
        "Pack experiência": os.getenv("STRIPE_PRICE_ID_PACK_EXPERIENCIA", "price_1RbNZPRGn5VRPX0U0xgDkQIu"),
        "Mensalidade Kula": os.getenv("STRIPE_PRICE_ID_MENSALIDADE_KULA", "price_1RbNphRGn5VRPX0UsNk4m7fS"),
        "Mensalidade Samadhi": os.getenv("STRIPE_PRICE_ID_MENSALIDADE_SAMADHI", "price_1RbNsWRGn5VRPX0UgGi1kkBn"),
        "Mensalidade Sadhana": os.getenv("STRIPE_PRICE_ID_MENSALIDADE_SADHANA", "price_1RbNsWRGn5VRPX0UgGi1kkBn"),
        "Pack família": os.getenv("STRIPE_PRICE_ID_PACK_FAMILIA", "price_1RbNphRGn5VRPX0UsNk4m7fS"),
    }

    # Configuração do banco de dados (Adicionado para ser usado em db_utils.py)
    DB_HOST: str = os.getenv("DB_HOST")
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_NAME: str = os.getenv("DB_NAME")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DATABASE_URL: str = os.getenv("DATABASE_URL") # Adicionado para suportar URL completa


settings = Settings()

if not settings.OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY não está definida nas variáveis de ambiente.")
if not settings.STRIPE_API_KEY:
    raise ValueError("STRIPE_API_KEY não está definida nas variáveis de ambiente.")
if not settings.STRIPE_WEBHOOK_SECRET: # Nova verificação
    print("Aviso: STRIPE_WEBHOOK_SECRET não está definido. O webhook do Stripe não funcionará.")
if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD or not settings.EMAIL_SENDER:
    print("Aviso: Credenciais de EMAIL não estão totalmente configuradas. O envio de e-mails pode falhar.")