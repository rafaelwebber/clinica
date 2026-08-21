from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy.sql import text
from werkzeug.security import check_password_hash, generate_password_hash
import db
from services.auth_security import (
    ROLE_ADMIN,
    limpar_falhas_login,
    login_bloqueado,
    registrar_falha_login,
    revogar_token,
    role_required,
)

bp = Blueprint("admin", __name__)


@bp.post("/api/v1/admin/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip()
    senha = data.get("senha")
    ip = request.remote_addr or "unknown"

    if not email or not senha:
        return jsonify({"error": "email e senha obrigatorios"}), 400

    bloqueado, segundos = login_bloqueado(ip, email)
    if bloqueado:
        return jsonify({
            "error": "muitas tentativas. tente novamente mais tarde",
            "retry_after_segundos": segundos,
        }), 429

    conn = db.SessionLocal()
    try:
        row = conn.execute(
            text("SELECT usuario_id, role_id, senha FROM usuarios WHERE email = :email"),
            {"email": email},
        ).mappings().fetchone()

        if not row or not check_password_hash(row["senha"], senha):
            ficou_bloqueado, lock_segundos = registrar_falha_login(ip, email)
            if ficou_bloqueado:
                return jsonify({
                    "error": "muitas tentativas. tente novamente mais tarde",
                    "retry_after_segundos": lock_segundos,
                }), 429
            return jsonify({"error": "senha ou email invalidos"}), 401

        limpar_falhas_login(ip, email)
        identity = str(row["usuario_id"])
        claims = {"role_id": row["role_id"]}
        access = create_access_token(identity=identity, additional_claims=claims)
        refresh = create_refresh_token(identity=identity, additional_claims=claims)

        return jsonify({
            "acesso": access,
            "refresh": refresh,
            "token_type": "Bearer",
            "expires_in_minutos": 15,
        }), 200
    finally:
        conn.close()


@bp.post("/api/v1/admin/refresh")
@jwt_required(refresh=True)
def refresh():
    """Troca o refresh atual por access + refresh novos (rotação)."""
    user_id = get_jwt_identity()
    claims = {"role_id": get_jwt().get("role_id")}
    revogar_token(get_jwt()["jti"])
    novo_access = create_access_token(identity=user_id, additional_claims=claims)
    novo_refresh = create_refresh_token(identity=user_id, additional_claims=claims)
    return jsonify({
        "acesso": novo_access,
        "refresh": novo_refresh,
        "token_type": "Bearer",
        "expires_in_minutos": 15,
    }), 200


@bp.post("/api/v1/admin/logout")
@jwt_required(verify_type=False)
def logout():

    revogar_token(get_jwt()["jti"])
    return jsonify({"mensagem": "logout realizado"}), 200


@bp.get("/api/v1/admin/user")
@jwt_required()
@role_required(ROLE_ADMIN)
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
@jwt_required()
@role_required(ROLE_ADMIN)
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
    try:
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
            return jsonify({"mensagem": "usuario criado com sucesso!"}), 201

    finally:
        criar.close()
            
@bp.post("/api/v1/admin/cliente")
@jwt_required()
@role_required(ROLE_ADMIN)
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
            return jsonify ({"mensage": "cliente criado com sucesso"}), 201
    finally:

        conn.close()

@bp.get("/api/v1/admin/cliente")
@jwt_required()
@role_required(ROLE_ADMIN)
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


