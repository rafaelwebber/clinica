from sqlalchemy import CHAR, Column, DateTime, Integer, String
from db import Base


class Clinica(Base):
    __tablename__ = "clinicas"

    id_clinica = Column(Integer, primary_key=True)
    nome = Column(String(100))
    cnpj = Column(String(14), unique=True)
    telefone = Column(String(15))
    email = Column(String(100), unique=True)
    senha = Column(String(500))
    cep = Column(String(8))
    uf = Column(CHAR(2))
    cidade = Column(String(100))
    bairro = Column(String(100))
    rua = Column(String(100))
    numero = Column(String(10))
    complemento = Column(String(100))
    status = Column(String(20))
    create_data = Column(DateTime)
    update_data = Column(DateTime)