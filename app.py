from flask import Flask
from api.operacional import bp as operacional
from db import SessionLocal, engine, Base
from models.clientes import Cliente
from models.usuarios import Usuario, Role
from models.consultas import Consulta
from models.lembrete import Template, Lembrete
from api.admin import bp as admin
import os 
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = os.getenv("SECRET_KEY") 
jwt = JWTManager(app)

Base.metadata.create_all(bind=engine)

app.register_blueprint(admin)
app.register_blueprint(operacional)

if __name__ == "__main__":
    app.run(debug=True)