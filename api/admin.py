from datetime import datetime
from flask import Flask, request, Blueprint, jsonify
from sqlalchemy.engine import row
from sqlalchemy.sql import text
from werkzeug.security import generate_password_hash

import db


bp = Blueprint("admin", __name__)


@bp.get("/api/v1/admin/user")
def listar_usuario():
    listar = db.SessionLocal()
    try:
        resultado= listar.execute(text(""" SELECT nome, role_id, cpf, rg, data_nascimento, email, telefone, telefone_secundario, create_data FROM usuarios
        """))
        usuarios = [dict(row) for row in resultado.mappings()]

        if not usuarios:
            return jsonify({"erro": "nao existe usuarios cadastrados"}), 404
        else:            
            return jsonify(usuarios)
    finally:
        listar.close()

@bp.post("/api/v1/admin/user")
def create_usuario():
    payload = request.get_json() or {}
    nome = payload.get("nome")
    role_id = payload.get("role_id")
    cpf = payload.get("cpf")
    rg = payload.get("rg")
    data_nascimento = payload.get("data_nascimento")
    email = payload.get("email")
    telefone = payload.get("telefone")
    telefone_secundario = payload.get("telefone_secundario")
    senha = payload.get("senha")
    create_data = datetime.now()

    if not nome or not cpf or not email or not senha or not create_data:
        return jsonify({"error": "campos obrgatorios"}), 400
    
    else:
        senha_hash = generate_password_hash(senha)
        criar = db.SessionLocal()
        criar.execute(
            text(
        """ 
            INSERT INTO usuarios
                (nome, role_id, cpf, rg, data_nascimento, email, telefone, telefone_secundario, senha, create_data) 
            VALUES (:nome, :role_id, :cpf, :rg, :data_nascimento, :email,
            :telefone, :telefone_secundario, :senha, :create_data)
        """
        ),
            {
            "nome": nome,
            "role_id": role_id,
            "cpf": cpf,
            "rg": rg,
            "data_nascimento": data_nascimento,
            "email": email,
            "telefone": telefone,
            "telefone_secundario": telefone_secundario,
            "senha": senha_hash,
            "create_data": create_data,           
        },
        )
        criar.commit()
        criar.close()
        return jsonify({"mensagem": "usuario criado com sucesso!"}), 201

@bp.post("/api/v1/admin/cliente")
def create_cliente():
    payload = request.get_json() or {}

    nome = payload.get("nome")
    nome_pai = payload.get("nome_pai")
    nome_mae = payload.get("nome_mae")
    estado_civil = payload.get("estado_civil")
    cpf = payload.get("cpf")
    rg = payload.get("rg")
    data_nascimento = payload.get("data_nascimento")
    idade = payload.get("idade")
    alergico = payload.get("alergico")
    observacao = payload.get("observacao")
    email = payload.get("email")
    telefone = payload.get("telefone")
    telefone_secundario = payload.get("telefone_secundario")
    cep = payload.get("cep")
    uf = payload.get("uf")
    cidade = payload.get("cidade")
    bairro = payload.get("bairro")
    rua = payload.get("rua")
    numero = payload.get('numero')
    create_data = datetime.now()

    try:
        if not nome or not email or not telefone:
            return jsonify({"error": "campos obrigatorios"}), 400

        else:
            conn = db.SessionLocal()
            conn.execute(text(
                """
                    INSERT INTO cliente (nome, nome_pai, nome_mae, estado_civil, cpf, rg, data_nascimento, idade, alergico, observacao, email, telefone, telefone_secundario, cep, uf, cidade, bairro, rua, numero, create_data)
                VALUES(:nome, :nome_pai, :nome_mae, :estado_civil, :cpf, :rg, :data_nascimento, :idade, :alergico, :observacao, :email, :telefone, :telefone_secundario, :cep, :uf, :cidade, :bairro, :rua, :numero, :create_data)"""
            ),
            {
                "nome": nome,
                "nome_pai":nome_pai,
                "nome_mae":nome_mae,
                "estado_civil": estado_civil,
                "cpf": cpf,
                "rg": rg,
                "data_nascimento": data_nascimento,
                "idade": idade,
                "alergico": alergico,
                "observacao": observacao,
                "email": email,
                "telefone": telefone,
                "telefone_secundario": telefone_secundario,
                "cep": cep,
                "uf": uf,
                "cidade": cidade,
                "bairro": bairro,
                "rua": rua,
                "numero": numero,
                "create_data": create_data
            },
            )           
            conn.commit()
            conn.close()
            return jsonify ({"mensage": "cliente criado com sucesso"}), 201
    finally:

        conn.close()

@bp.get("/api/v1/admin/cliente")
def listar_clientes():
    conn = db.SessionLocal()

    try:
        resultado = conn.execute(text("""
            SELECT * FROM cliente
        """))
        cliente = [dict(row) for row in resultado.mappings()]
        if not cliente:
            return jsonify({"error": "Nenhum cliente cadastrado"})
        else:
            return jsonify(cliente), 200

    finally:
        conn.close()