from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String
from db import Base
from models.clinicas import Clinica


class Promocoes(Base):
    __tablename__ = "promocoes"

    id_promocao = Column(Integer, primary_key=True)
    id_clinica = Column(Integer, ForeignKey(Clinica.id_clinica), nullable=False)
    nome = Column(String(50))
    descricao = Column(String(200))
    valor = Column(Float)
    data_inicio = Column(Date)
    data_fim = Column(Date)
    status = Column(String(20))
    create_data = Column(DateTime)
    update_data = Column(DateTime)
