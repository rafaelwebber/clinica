from sqlalchemy import CHAR, Boolean, Column, Date, Integer, String, VARCHAR, DateTime
from db import Base

class Cliente(Base):
    __tablename__ = "cliente"

    id_cliente = Column(Integer, primary_key=True)
    #dados pessoais
    nome = Column(String(100))
    nome_pai = Column(String(100))
    nome_mae = Column(String(100))
    estado_civil = Column(String(100))
    cpf = Column(VARCHAR(11))
    rg = Column(VARCHAR(9))
    data_nascimento = Column(Date)
    idade = Column(Integer)
    alergico = Column(Boolean)
    observacao = Column(String(200))
    #contatos
    email = Column(String(100))
    telefone = Column(VARCHAR(11))
    telefone_secundario = Column(VARCHAR(11))
    #localizacao
    cep = Column(VARCHAR(8))
    uf = Column(CHAR)   
    cidade = Column(String(100))
    bairro = Column(String(200))
    rua = Column(String(200))
    numero = Column(String(20))
    
    create_data = Column(DateTime)
    update_data = Column(DateTime)



