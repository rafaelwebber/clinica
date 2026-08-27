from sqlalchemy import (
    CHAR,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    VARCHAR,
)
from db import Base
from models.clinicas import Clinica


class Cliente(Base):
    __tablename__ = "cliente"
    __table_args__ = (
        UniqueConstraint("cpf", "id_clinica", name="uq_cliente_cpf_clinica"),
        UniqueConstraint("rg", "id_clinica", name="uq_cliente_rg_clinica"),
        UniqueConstraint("email", "id_clinica", name="uq_cliente_email_clinica"),
    )

    id_cliente = Column(Integer, primary_key=True)
    id_clinica = Column(Integer, ForeignKey(Clinica.id_clinica), nullable=False)
    nome = Column(String(100))
    nome_pai = Column(String(100))
    nome_mae = Column(String(100))
    estado_civil = Column(String(100))
    cpf = Column(VARCHAR(11))
    rg = Column(VARCHAR(20))
    data_nascimento = Column(Date)
    idade = Column(Integer)
    alergico = Column(Boolean)
    observacao = Column(String(200))
    email = Column(String(100))
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
