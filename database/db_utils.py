# database/db_utils.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base, Appointment, AppointmentStatus # Importa Base, Appointment e AppointmentStatus
from datetime import date, time
from typing import List, Optional

from app.config import settings

# Configuração do banco de dados
# Use a string de conexão do DATABASE_URL (Railway/Heroku/etc) ou SQLite local como fallback
if settings.DATABASE_URL: # Preferir DATABASE_URL se estiver definida (mais comum em produção)
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
elif settings.DB_HOST: # Fallback para variáveis separadas (para PostgreSQL)
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@"
        f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else: # Fallback para SQLite local
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_and_tables():
    Base.metadata.create_all(engine)

def get_db():
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
        status=AppointmentStatus.pending # Status inicial como pendente
    )
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)
    return new_appointment

def get_appointment_by_id(db: Session, appointment_id: int) -> Optional[Appointment]:
    return db.query(Appointment).filter(Appointment.id == appointment_id).first()

# MODIFICADO: Retorna LISTA de objetos Appointment, não mais a contagem.
def get_appointments_for_date_time(db: Session, target_date: date, target_time: time, class_type: str) -> List[Appointment]:
    return db.query(Appointment).filter(
        Appointment.appointment_date == target_date,
        Appointment.appointment_time == target_time,
        Appointment.class_type == class_type # Adicionado class_type para filtrar por aula específica
    ).all() # Retorna todos os objetos, não a contagem

def update_appointment_status(db: Session, appointment_id: int, new_status: AppointmentStatus) -> Optional[Appointment]:
    appointment = get_appointment_by_id(db, appointment_id)
    if appointment:
        appointment.status = new_status
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