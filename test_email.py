import os
import sys
from datetime import date, time
from app.config import settings

# Configurar caminhos
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))

# Agora importe o settings
from app.config import settings

# Importar a função de envio de email
from utils.email_sender import send_email

# Dados de teste
test_details = {
    'client_name': 'Teste',
    'class_type': 'Hatha Yoga',
    'appointment_date': date(2025, 6, 20),
    'appointment_time': time(10, 0),
    'client_phone': '+351123456789',
    'client_email': 'cliente@teste.com'
}

print("Enviando e-mail de teste...")
result = send_email(
    to_email="igorraposo02@gmail.com",  # COLOQUE SEU EMAIL AQUI
    email_type="client_confirmation",
    appointment_details=test_details,
    language="pt"
)

if result:
    print(" E-mail enviado com sucesso!")
else:
    print(" Falha ao enviar e-mail")