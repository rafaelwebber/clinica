from sqlalchemy import CHAR, Boolean, Column, Date, DateTime, Integer, String, VARCHAR
from db import Base


class Cliente(Base):
    __tablename__ = "cliente"

    id_cliente = Column(Integer, primary_key=True)
    nome = Column(String(100))
    nome_pai = Column(String(100))
    nome_mae = Column(String(100))
    estado_civil = Column(String(100))
    cpf = Column(VARCHAR(11), unique=True)
    rg = Column(VARCHAR(20), unique=True)
    data_nascimento = Column(Date)
    idade = Column(Integer)
    alergico = Column(Boolean)
    observacao = Column(String(200))
    email = Column(String(100), unique=True)
    telefone = Column(VARCHAR(15))
    telefone_secundario = Column(VARCHAR(15))
    cep = Column(VARCHAR(8))
    uf = Column(CHAR(2))
    cidade = Column(String(100))
    bairro = Column(String(200))
    rua = Column(String(200))
    numero = Column(String(20))

    create_data = Column(DateTime)
    update_data = Column(DateTime)
