from sqlalchemy import Date, ForeignKey, Integer, String, Column
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
    cpf = Column(Integer)
    rg = Column(Integer)
    data_nascimento = Column(Date)
    email = Column(String(100))
    telefone = Column(Integer)
    telefone_secundario = Column(Integer)
    senha = Column(String(200))
    
    create_data = Column(Date)
    update_data = Column(Date)

