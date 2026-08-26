from db import Base
from sqlalchemy import Column, Date, ForeignKey, Integer, String, Time, DateTime
from models.consultas import Consulta



class Template(Base):
    __tablename__= "template"

    id_mensagem = Column(Integer, primary_key=True)
    
    titulo = Column(String(50))
    conteudo = Column(String(200))
    
    create_data = Column(DateTime)
    update_data = Column(DateTime)



class Lembrete(Base):
    __tablename__ = "lembrete"

    id_lembrete = Column(Integer, primary_key=True)
    id_mensagem = Column(Integer, ForeignKey(Template.id_mensagem), nullable=False)

    data_disparo = Column(Date)
    horario_disparo = Column(Time)
    tipo_disparo = Column(String(50))
    status = Column(String(10))

    create_data = Column(DateTime)
    update_data = Column(DateTime)   


    