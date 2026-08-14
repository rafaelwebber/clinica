from flask import Flask, request, Blueprint, jsonify
from sqlalchemy.sql import text
from models.usuarios import Usuario

import db


bp = Blueprint("admin", __name__)


@bp.get("/api/v1/admin/user")
def listar_usuario():
    listar = db.SessionLocal()

    usuarios = listar.get(Usuario, "nome")
    if not usuarios:
        return jsonify({"erro": "nao existe usuarios cadastrados"}), 404
    else:
        
        return jsonify(usuarios)
    


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
    create_data = payload.get("create_data")
    update_data = payload.get("update_data")

    if not nome or not cpf or not email or not senha or not create_data:
        return jsonify({"error": "campos obrgatorios"}), 400
    
    else:
        criar = db.SessionLocal()
        criar.execute(
            text(
        """ 
            INSERT INTO usuarios
                (nome, role_id, cpf, rg, data_nascimento, email, telefone, telefone_secundario, senha, create_data, update_data ) 
            VALUES (:nome, :role_id, :cpf, :rg, :data_nascimento, :email,
            :telefone, :telefone_secundario, :senha, :create_data, :update_data)
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
            "senha": senha,
            "create_data": create_data,
            "update_data": update_data,
        },
        )
        criar.commit()
        criar.close()
        return jsonify({"mensagem": "usuario criado com sucesso!"}), 201
