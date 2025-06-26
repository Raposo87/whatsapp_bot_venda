# database/db_utils.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base, Appointment, AppointmentStatus
from datetime import date, time
from typing import List, Optional

from app.config import settings # Importa o objeto settings

# Variável global para o engine, inicializada aqui
engine = None
SQLALCHEMY_DATABASE_URL = None

# Configuração do banco de dados
# Tenta usar DATABASE_URL (para Railway/Heroku/etc), depois DB_HOST (para PostgreSQL), ou SQLite local como fallback
if settings.DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
elif settings.DB_HOST: # Fallback para variáveis separadas (para PostgreSQL)
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@"
        f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
else: # Fallback para SQLite local
    # Caminho para o app.db, garantindo que ele esteja na raiz do projeto
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

# Garante que o engine é criado APÓS a URL ser definida
try:
    if SQLALCHEMY_DATABASE_URL:
        if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
            engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
        else:
            engine = create_engine(SQLALCHEMY_DATABASE_URL)
    else:
        raise ValueError("DATABASE_URL não definida em settings e fallback para SQLite falhou.")
except Exception as e:
    print(f"Erro ao criar o engine do banco de dados: {e}")
    print("Verifique suas variáveis de ambiente de banco de dados no .env.")
    # É crucial que a aplicação não continue se o engine não puder ser criado
    exit(1)


# SessionLocal deve ser definida APÓS o engine ter sido criado
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_db_and_tables():
    """Cria as tabelas no banco de dados com base nos modelos."""
    # Garante que Base.metadata tenha conhecimento de todas as tabelas definidas
    # antes de tentar criá-las.
    Base.metadata.create_all(engine)

def get_db():
    """Retorna uma sessão de banco de dados para uso."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_appointment_in_db(
    db: Session,
    client_name: str,
    client_phone: str,
    client_email: str,
    class_type: str,
    appointment_date: date,
    appointment_time: time
) -> Appointment:
    new_appointment = Appointment(
        client_name=client_name,
        client_phone=client_phone,
        client_email=client_email,
        class_type=class_type,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        status=AppointmentStatus.pending
    )
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)
    return new_appointment

def get_appointment_by_id(db: Session, appointment_id: int) -> Optional[Appointment]:
    return db.query(Appointment).filter(Appointment.id == appointment_id).first()

def get_appointments_for_date_time(db: Session, target_date: date, target_time: time, class_type: str) -> List[Appointment]:
    return db.query(Appointment).filter(
        Appointment.appointment_date == target_date,
        Appointment.appointment_time == target_time,
        Appointment.class_type == class_type
    ).all()

def update_appointment_status_only(db: Session, appointment_id: int, new_status: AppointmentStatus) -> Optional[Appointment]:
    appointment = get_appointment_by_id(db, appointment_id)
    if appointment:
        appointment.status = new_status
        db.commit()
        db.refresh(appointment)
    return appointment

def update_appointment_status_and_payment(
    db: Session,
    appointment_id: int,
    new_status: AppointmentStatus,
    amount_paid: Optional[float] = None,
    commission_amount: Optional[float] = None,
    stripe_payment_id: Optional[str] = None
) -> Optional[Appointment]:
    appointment = get_appointment_by_id(db, appointment_id)
    if appointment:
        appointment.status = new_status
        if amount_paid is not None:
            appointment.amount_paid = amount_paid
        if commission_amount is not None:
            appointment.commission_amount = commission_amount
        if stripe_payment_id is not None:
            appointment.stripe_payment_id = stripe_payment_id

        db.commit()
        db.refresh(appointment)
    return appointment

def update_appointment_payment_link(db: Session, appointment_id: int, stripe_link: str) -> Optional[Appointment]:
    db_appointment = get_appointment_by_id(db, appointment_id)
    if db_appointment:
        db_appointment.stripe_payment_link = stripe_link
        db.commit()
        db.refresh(db_appointment)
    return db_appointment