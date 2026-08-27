from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Time
from db import Base
from models.clinicas import Clinica

class Template(Base):
    __tablename__ = "template"

    id_mensagem = Column(Integer, primary_key=True)
    id_clinica = Column(Integer, ForeignKey(Clinica.id_clinica), nullable=False)
    titulo = Column(String(50))
    conteudo = Column(String(2000))

    create_data = Column(DateTime)
    update_data = Column(DateTime)


class Lembrete(Base):
    __tablename__ = "lembrete"

    id_lembrete = Column(Integer, primary_key=True)
    id_mensagem = Column(Integer, ForeignKey(Template.id_mensagem), nullable=False)
    id_clinica = Column(Integer, ForeignKey(Clinica.id_clinica), nullable=False)
    data_disparo = Column(Date)
    horario_disparo = Column(Time)
    tipo_disparo = Column(String(50))
    status = Column(String(20))

    create_data = Column(DateTime)
    update_data = Column(DateTime)
