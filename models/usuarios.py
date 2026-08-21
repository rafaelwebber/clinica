from sqlalchemy import VARCHAR, Date, ForeignKey, Integer, String, Column, DateTime
from db import Base


class Role(Base):
    __tablename__="Role"
    role_id = Column(Integer, primary_key=True)
    role_name = Column(String(50), unique=True, nullable=False)

class Usuario(Base):
    __tablename__= "usuarios"

    usuario_id = Column(Integer, primary_key=True)
    role_id = Column(Integer,ForeignKey(Role.role_id), nullable=False)

    nome = Column(String(100))
    cpf = Column(VARCHAR(11))
    rg = Column(VARCHAR(9))
    data_nascimento = Column(Date)
    email = Column(String(100))
    telefone = Column(VARCHAR(11))
    telefone_secundario = Column(VARCHAR(11))
    senha = Column(String(500))
    
    create_data = Column(DateTime)
    update_data = Column(DateTime)

