# database/models.py

import enum
from sqlalchemy import Column, Integer, String, Date, Time, Enum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class AppointmentStatus(enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    paid = "paid"
    cancelled = "cancelled"

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, index=True, nullable=False)
    client_phone = Column(String, nullable=False)
    client_email = Column(String, nullable=False)
    class_type = Column(String, nullable=False)
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.pending, nullable=False)
    stripe_payment_link = Column(String, nullable=True)

    def __repr__(self):
        return (f"<Appointment(id={self.id}, client_name='{self.client_name}', "
                f"class_type='{self.class_type}', date={self.appointment_date}, "
                f"time={self.appointment_time}, status='{self.status.value}')>")