import datetime
from sqlalchemy import ForeignKey, Integer, Column, String, Date, Time, DateTime
from db import Base
from models.clientes import Cliente

class Consulta(Base):
    __tablename__ ="consultas"

    id_consulta = Column(Integer, primary_key=True)
    id_cliente = Column(Integer, ForeignKey(Cliente.id_cliente), nullable=False)

    profissional_responsavel = Column(String(100))
    tipo_consulta = Column(String(50))
    status = Column(String(50))
    observacao= Column(String(200))
    retorno = Column(Date)
    horario = Column(Time)

    create_data = Column(DateTime)
    update_data = Column(DateTime)