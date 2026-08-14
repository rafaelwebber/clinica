from sqlalchemy import CHAR, Boolean, Column, Date, Integer, String
from db import Base

class Cliente(Base):
    __tablename__ = "cliente"

    id_cliente = Column(Integer, primary_key=True)
    #dados pessoais
    nome = Column(String(100))
    nome_pai = Column(String(100))
    nome_mae = Column(String(100))
    estado_civil = Column(String(100))
    cpf = Column(Integer)
    rg = Column(Integer)
    data_nascimento = Column(Date)
    idade = Column(Integer)
    alergico = Column(Boolean)
    observacao = Column(String(200))
    #contatos
    email = Column(String(100))
    telefone = Column(Integer)
    telefone_secundario = Column(Integer)
    #localizacao
    cep = Column(Integer)
    uf = Column(CHAR)   
    cidade = Column(String(100))
    bairro = Column(String(200))
    rua = Column(String(200))
    numero = Column(Integer)
    
    create_data = Column(Date)
    update_data = Column(Date)



