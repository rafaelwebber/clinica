from flask import Flask
from api.operacional import bp as operacional
from db import SessionLocal, engine, Base
from models.clientes import Cliente
from models.usuarios import Usuario, Role
from models.consultas import Consulta
from api.admin import bp as admin

app = Flask(__name__)

Base.metadata.create_all(bind=engine)

# @app.route.route("/")
# def home():
#     return "ok"

app.register_blueprint(admin)
app.register_blueprint(operacional)

if __name__ == "__main__":
    app.run(debug=True)