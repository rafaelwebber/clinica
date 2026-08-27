from datetime import timedelta
import os

from dotenv import load_dotenv
from flask import Flask
from flask_jwt_extended import JWTManager
from sqlalchemy import text

from api.admin import bp as admin
from api.operacional import bp as operacional
from db import Base, engine
from models.clientes import Cliente
from models.clinicas import Clinica
from models.consultas import Consulta
from models.lembrete import Lembrete, Template
from models.usuarios import Role, TokenRevogado, Usuario
from models.promocoes import Promocoes
from services.auth_security import token_na_blocklist

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY nao configurada")

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)

jwt = JWTManager(app)


@jwt.token_in_blocklist_loader
def checar_token_revogado(jwt_header, jwt_payload):
    return token_na_blocklist(jwt_payload["jti"])


Base.metadata.create_all(bind=engine)

app.register_blueprint(admin)
app.register_blueprint(operacional)

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "true").lower() in ("1", "true", "yes"))
