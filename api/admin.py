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
    validar_senha,
)

bp = Blueprint("admin", __name__)


@bp.post("/api/v1/admin/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip()
    senha = data.get("senha").strip()
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
# @jwt_required()
# @role_required(ROLE_ADMIN)
def create_usuario():
    payload = request.get_json() or {}
    nome = payload.get("nome").strip()
    role_id = payload.get("role_id")
    cpf = payload.get("cpf").strip()
    rg = (payload.get("rg") or "").strip()
    data_nascimento = payload.get("data_nascimento").strip()
    email = payload.get("email").strip()
    telefone = (payload.get("telefone") or "").strip()
    telefone_secundario = (payload.get("telefone_secundario") or "").strip()
    senha = payload.get("senha").strip()
    create_data = datetime.now()

    criar = db.SessionLocal()
    try:
        if not nome or not cpf or not email or not senha or not create_data:
            return jsonify({"error": "campos obrigatorios não preenchidos"}), 409

        if not validar_senha(senha):
            return jsonify({"error": "senha tem que conter pelo menos 8 Caracteres, uma letra maiuscula, uma letra minuscula, um numero e um caracter especial"}), 400
        
        
        senha_hash = generate_password_hash(senha)
        
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

@bp.patch("/api/v1/admin/user/<int:user_id>")
@jwt_required()
@role_required(ROLE_ADMIN)
def update_usuario(user_id):
    payload = request.get_json() or {}
    campos = {}

    for chave in (
        "nome",
        "cpf",
        "rg",
        "data_nascimento",
        "email",
        "telefone",
        "telefone_secundario",
    ):
        if chave in payload and payload[chave] is not None:
            campos[chave] = str(payload[chave]).strip()

    if "role_id" in payload and payload["role_id"] is not None:
        campos["role_id"] = payload["role_id"]

    if "senha" in payload and payload["senha"]:
        senha = str(payload["senha"]).strip()
        if not validar_senha(senha):
            return jsonify({
                "error": (
                    "senha tem que conter pelo menos 8 Caracteres, uma letra maiuscula, "
                    "uma letra minuscula, um numero e um caracter especial"
                )
            }), 409
        campos["senha"] = generate_password_hash(senha)

    if not campos:
        return jsonify({"error": "nenhum campo para atualizar"}), 400

    campos["update_data"] = datetime.now()
    sets = ", ".join(f"{coluna} = :{coluna}" for coluna in campos)
    campos["user_id"] = user_id

    atualizar = db.SessionLocal()
    try:
        resultado = atualizar.execute(
            text(f"UPDATE usuarios SET {sets} WHERE usuario_id = :user_id"),
            campos,
        )
        if resultado.rowcount == 0:
            return jsonify({"error": "usuario nao encontrado"}), 404
        atualizar.commit()
        return jsonify({"mensagem": "usuario atualizado com sucesso!"}), 200
    finally:
        atualizar.close()

@bp.post("/api/v1/admin/clientes")
@jwt_required()
@role_required(ROLE_ADMIN)
def create_cliente():
    payload = request.get_json() or {}

    nome = payload.get("nome").strip()
    nome_pai = payload.get("nome_pai").strip()
    nome_mae = payload.get("nome_mae").strip()
    estado_civil = payload.get("estado_civil").strip()
    cpf = payload.get("cpf").strip()    
    rg = payload.get("rg").strip()
    data_nascimento = payload.get("data_nascimento").strip()
    idade = payload.get("idade").strip()
    alergico = payload.get("alergico").strip()
    observacao = payload.get("observacao").strip()
    email = payload.get("email").strip()
    telefone = payload.get("telefone").strip()
    telefone_secundario = payload.get("telefone_secundario").strip()
    cep = payload.get("cep").strip()
    uf = payload.get("uf").strip()
    cidade = payload.get("cidade").strip()
    bairro = payload.get("bairro").strip()
    rua = payload.get("rua").strip()
    numero = payload.get('numero').strip()
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

@bp.get("/api/v1/admin/clientes")
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

@bp.patch("/api/v1/admin/clientes/<int:cliente_id>")
@jwt_required()
@role_required(ROLE_ADMIN)
def update_cliente(cliente_id):
    payload = request.get_json() or {}
    campos = {}

    for chave in (
        "nome",
        "nome_pai",
        "nome_mae",
        "estado_civil",
        "cpf",
        "rg",
        "data_nascimento",
        "observacao",
        "email",
        "telefone",
        "telefone_secundario",
        "cep",
        "uf",
        "cidade",
        "bairro",
        "rua",
        "numero",
    ):
        if chave in payload and payload[chave] is not None:
            campos[chave] = str(payload[chave]).strip()

    if "idade" in payload and payload["idade"] is not None:
        campos["idade"] = payload["idade"]

    if "alergico" in payload and payload["alergico"] is not None:
        campos["alergico"] = payload["alergico"]

    if not campos:
        return jsonify({"error": "nenhum campo para atualizar"}), 400

    campos["update_data"] = datetime.now()
    sets = ", ".join(f"{coluna} = :{coluna}" for coluna in campos)
    campos["cliente_id"] = cliente_id

    conn = db.SessionLocal()
    try:
        resultado = conn.execute(
            text(f"UPDATE cliente SET {sets} WHERE id_cliente = :cliente_id"),
            campos,
        )
        if resultado.rowcount == 0:
            return jsonify({"error": "cliente nao encontrado"}), 404
        conn.commit()
        return jsonify({"mensagem": "cliente atualizado com sucesso!"}), 200
    finally:
        conn.close()
