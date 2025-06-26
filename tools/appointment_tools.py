# tools/appointment_tools.py

from datetime import datetime, timedelta, date, time
from typing import Optional
from sqlalchemy.orm import Session
from langchain.tools import tool
from utils.email_sender import send_email # Ainda importado para outras ferramentas
from pydantic import BaseModel, Field

# Importa as funções utilitárias do banco de dados
from database.db_utils import (
    get_db,
    create_appointment_in_db,
    get_appointment_by_id,
    get_appointments_for_date_time,
    update_appointment_status_only
)
from database.models import Appointment, AppointmentStatus # Importar AppointmentStatus para definir o default

MAX_APPOINTMENTS_PER_SLOT = 2

class CheckAppointmentAvailabilityInput(BaseModel):
    date_str: str = Field(..., description="Data no formato DD-MM-YYYY (ex: 31-12-2025)")
    time_str: str = Field(..., description="Hora no formato HH:MM (ex: 15:00)")
    class_type: str = Field(..., description="Tipo de aula de yoga (ex: Hatha Yoga, Vinyasa Yoga, Yoga Suave, etc.)")

@tool(args_schema=CheckAppointmentAvailabilityInput)
def check_appointment_availability(date_str: str, time_str: str, class_type: str) -> str:
    """
    Verifica se há disponibilidade para um tipo de AULA DE YOGA em uma data e hora específicas.
    """
    db_session = next(get_db())
    try:
        requested_date = datetime.strptime(date_str, '%d-%m-%Y').date()
        requested_time = datetime.strptime(time_str, '%H:%M').time()

        # Obter agendamentos existentes para a data e hora
        existing_appointments = get_appointments_for_date_time(db_session, requested_date, requested_time, class_type)

        # Contar apenas os agendamentos que não estão cancelados
        active_appointments_count = sum(1 for app in existing_appointments if app.status != AppointmentStatus.cancelled)


        if active_appointments_count < MAX_APPOINTMENTS_PER_SLOT:
            remaining_slots = MAX_APPOINTMENTS_PER_SLOT - active_appointments_count
            return f"Sim, há vagas disponíveis para {class_type} em {date_str} às {time_str}. Restam {remaining_slots} vagas."
        else:
            return f"Não há vagas disponíveis para {class_type} em {date_str} às {time_str}. A aula está lotada."
    except ValueError:
        return "Formato de data ou hora inválido. Por favor, use DD-MM-YYYY para a data e HH:MM para a hora."
    except Exception as e:
        return f"Ocorreu um erro ao verificar a disponibilidade: {e}"
    finally:
        db_session.close()


class CreateNewAppointmentInput(BaseModel):
    client_name: str = Field(..., description="Nome completo do cliente")
    client_phone: str = Field(..., description="Número de telefone do cliente (com código de país, ex: +351912345678)")
    client_email: str = Field(..., description="Endereço de email do cliente")
    class_type: str = Field(..., description="Tipo de aula de yoga (ex: Hatha Yoga, Vinyasa Yoga, Yoga Suave, etc.)")
    date_str: str = Field(..., description="Data do agendamento no formato DD-MM-YYYY (ex: 31-12-2025)")
    time_str: str = Field(..., description="Hora do agendamento no formato HH:MM (ex: 15:00)")
    language: str = Field("pt", description="Idioma para o e-mail de confirmação (pt, en)")

@tool(args_schema=CreateNewAppointmentInput)
def create_new_appointment(
    client_name: str,
    client_phone: str,
    client_email: str,
    class_type: str,
    date_str: str,
    time_str: str,
    language: str = 'pt'
) -> str:
    """
    Cria um novo agendamento de aula de yoga para um cliente.
    O agendamento é inicialmente criado como 'pending' e requer pagamento para confirmação.
    """
    db_session = None
    try:
        db_session = next(get_db())

        appointment_date = datetime.strptime(date_str, '%d-%m-%Y').date()
        appointment_time = datetime.strptime(time_str, '%H:%M').time()

        # Criar o agendamento no banco de dados com status 'pending'
        new_appointment = create_appointment_in_db(
            db_session,
            client_name,
            client_phone,
            client_email,
            class_type,
            appointment_date,
            appointment_time
        )
        db_session.commit()

        # NENHUM EMAIL É ENVIADO AQUI.
        # Tanto o cliente quanto a empresa só receberão a confirmação APÓS o pagamento ser confirmado via Stripe Webhook.

        return (f"Agendamento criado com sucesso! "
                f"ID do agendamento: {new_appointment.id}. "
                f"Aula: {new_appointment.class_type}. "
                f"Data: {new_appointment.appointment_date.strftime('%d-%m-%Y')}. "
                f"Hora: {new_appointment.appointment_time.strftime('%H:%M')}. "
                f"Aguarde o link de pagamento.")

    except ValueError as e:
        if db_session:
            db_session.rollback()
        return f"Erro no formato de dados: {e}. Por favor, verifique a data (DD-MM-YYYY) e hora (HH:MM)."
    except Exception as e:
        if db_session:
            db_session.rollback()
        logging.error(f"Erro inesperado ao agendar a aula: {e}", exc_info=True)
        return f"Ocorreu um erro inesperado ao agendar a aula: {e}. Por favor, tente novamente ou entre em contato diretamente."
    finally:
        if db_session:
            db_session.close()