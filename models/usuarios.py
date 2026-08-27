from sqlalchemy import VARCHAR, Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from db import Base
from models.clinicas import Clinica


class Role(Base):
    __tablename__ = "role"
    role_id = Column(Integer, primary_key=True)
    role_name = Column(String(50), unique=True, nullable=False)


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint("cpf", "id_clinica", name="uq_usuario_cpf_clinica"),
        UniqueConstraint("rg", "id_clinica", name="uq_usuario_rg_clinica"),
        UniqueConstraint("email", "id_clinica", name="uq_usuario_email_clinica"),
    )

    usuario_id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey(Role.role_id), nullable=False)
    id_clinica = Column(Integer, ForeignKey(Clinica.id_clinica), nullable=False)

    nome = Column(String(100))
    cpf = Column(VARCHAR(11))
    rg = Column(VARCHAR(20))
    data_nascimento = Column(Date)
    email = Column(String(100))
    telefone = Column(VARCHAR(15))
    telefone_secundario = Column(VARCHAR(15))
    senha = Column(String(500))

    create_data = Column(DateTime)
    update_data = Column(DateTime)


class TokenRevogado(Base):
    __tablename__ = "token_revogado"

    jti = Column(String(64), primary_key=True)
    criado_em = Column(DateTime)
