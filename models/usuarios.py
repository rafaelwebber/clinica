from sqlalchemy import VARCHAR, Date, DateTime, ForeignKey, Integer, String, Column
from db import Base


class Role(Base):
    __tablename__ = "role"
    role_id = Column(Integer, primary_key=True)
    role_name = Column(String(50), unique=True, nullable=False)


class Usuario(Base):
    __tablename__ = "usuarios"

    usuario_id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey(Role.role_id), nullable=False)

    nome = Column(String(100))
    cpf = Column(VARCHAR(11), unique=True)
    rg = Column(VARCHAR(20), unique=True)
    data_nascimento = Column(Date)
    email = Column(String(100), unique=True)
    telefone = Column(VARCHAR(15))
    telefone_secundario = Column(VARCHAR(15))
    senha = Column(String(500))

    create_data = Column(DateTime)
    update_data = Column(DateTime)


class TokenRevogado(Base):
    __tablename__ = "token_revogado"

    jti = Column(String(64), primary_key=True)
    criado_em = Column(DateTime)
