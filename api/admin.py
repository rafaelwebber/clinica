from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy.exc import IntegrityError
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
from services.helpers import (
    agora_sp,
    calcular_idade,
    para_bool,
    serializar_item,
    texto,
    vazio_para_none,
)

bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


@bp.post("/login")
def login():
    data = request.get_json() or {}
    email = texto(data.get("email"))
    senha = texto(data.get("senha"))
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
        claims = {"role_id": int(row["role_id"])}
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


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    try:
        claims = {"role_id": int(get_jwt().get("role_id"))}
    except (TypeError, ValueError):
        return jsonify({"error": "token invalido"}), 401
    revogar_token(get_jwt()["jti"])
    novo_access = create_access_token(identity=user_id, additional_claims=claims)
    novo_refresh = create_refresh_token(identity=user_id, additional_claims=claims)
    return jsonify({
        "acesso": novo_access,
        "refresh": novo_refresh,
        "token_type": "Bearer",
        "expires_in_minutos": 15,
    }), 200


@bp.post("/logout")
@jwt_required(verify_type=False)
def logout():
    revogar_token(get_jwt()["jti"])
    return jsonify({"mensagem": "logout realizado"}), 200


@bp.get("/usuarios")
@jwt_required()
@role_required(ROLE_ADMIN)
def listar_usuario():
    conn = db.SessionLocal()
    try:
        resultado = conn.execute(text(
            """
            SELECT usuario_id, nome, role_id, cpf, rg, data_nascimento, email,
                   telefone, telefone_secundario, create_data, update_data
            FROM usuarios
            """
        ))
        usuarios = [serializar_item(dict(row)) for row in resultado.mappings()]
        return jsonify(usuarios), 200
    finally:
        conn.close()


@bp.post("/usuarios")
@jwt_required()
@role_required(ROLE_ADMIN)
def create_usuario():
    payload = request.get_json() or {}
    nome = texto(payload.get("nome"))
    cpf = texto(payload.get("cpf"))
    rg = vazio_para_none(payload.get("rg"))
    data_nascimento = vazio_para_none(payload.get("data_nascimento"))
    email = texto(payload.get("email"))
    telefone = vazio_para_none(payload.get("telefone"))
    telefone_secundario = vazio_para_none(payload.get("telefone_secundario"))
    senha = texto(payload.get("senha"))
    create_data = agora_sp()

    try:
        role_id = int(payload.get("role_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "role_id invalido"}), 400

    if role_id not in (1, 2):
        return jsonify({"error": "role_id deve ser 1 (admin) ou 2 (operacional)"}), 400

    if not nome or not cpf or not email or not senha:
        return jsonify({"error": "campos obrigatorios nao preenchidos"}), 400

    if not validar_senha(senha):
        return jsonify({
            "error": (
                "senha tem que conter pelo menos 8 caracteres, uma letra maiuscula, "
                "uma letra minuscula, um numero e um caracter especial"
            )
        }), 400

    conn = db.SessionLocal()
    try:
        conn.execute(
            text(
                """
                INSERT INTO usuarios
                    (nome, role_id, cpf, rg, data_nascimento, email, telefone,
                     telefone_secundario, senha, create_data)
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
                "senha": generate_password_hash(senha),
                "create_data": create_data,
            },
        )
        conn.commit()
        return jsonify({"mensagem": "usuario criado com sucesso!"}), 201
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "cpf, rg ou email ja cadastrado"}), 409
    finally:
        conn.close()


@bp.patch("/usuarios/<int:user_id>")
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
            campos[chave] = vazio_para_none(payload[chave])

    if "role_id" in payload and payload["role_id"] is not None:
        try:
            role_id = int(payload["role_id"])
        except (TypeError, ValueError):
            return jsonify({"error": "role_id invalido"}), 400
        if role_id not in (1, 2):
            return jsonify({"error": "role_id deve ser 1 (admin) ou 2 (operacional)"}), 400
        campos["role_id"] = role_id

    if "senha" in payload and payload["senha"]:
        senha = texto(payload["senha"])
        if not validar_senha(senha):
            return jsonify({
                "error": (
                    "senha tem que conter pelo menos 8 caracteres, uma letra maiuscula, "
                    "uma letra minuscula, um numero e um caracter especial"
                )
            }), 400
        campos["senha"] = generate_password_hash(senha)

    if not campos:
        return jsonify({"error": "nenhum campo para atualizar"}), 400

    campos["update_data"] = agora_sp()
    sets = ", ".join(f"{coluna} = :{coluna}" for coluna in campos)
    campos["user_id"] = user_id

    conn = db.SessionLocal()
    try:
        resultado = conn.execute(
            text(f"UPDATE usuarios SET {sets} WHERE usuario_id = :user_id"),
            campos,
        )
        if resultado.rowcount == 0:
            return jsonify({"error": "usuario nao encontrado"}), 404
        conn.commit()
        return jsonify({"mensagem": "usuario atualizado com sucesso!"}), 200
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "cpf, rg ou email ja cadastrado"}), 409
    finally:
        conn.close()


@bp.post("/clientes")
@jwt_required()
@role_required(ROLE_ADMIN)
def create_cliente():
    payload = request.get_json() or {}

    nome = texto(payload.get("nome"))
    email = texto(payload.get("email"))
    telefone = texto(payload.get("telefone"))
    data_nascimento = vazio_para_none(payload.get("data_nascimento"))
    create_data = agora_sp()

    if not nome or not email or not telefone:
        return jsonify({"error": "campos obrigatorios"}), 400

    conn = db.SessionLocal()
    try:
        conn.execute(
            text(
                """
                INSERT INTO cliente (
                    nome, nome_pai, nome_mae, estado_civil, cpf, rg, data_nascimento,
                    idade, alergico, observacao, email, telefone, telefone_secundario,
                    cep, uf, cidade, bairro, rua, numero, create_data
                ) VALUES (
                    :nome, :nome_pai, :nome_mae, :estado_civil, :cpf, :rg, :data_nascimento,
                    :idade, :alergico, :observacao, :email, :telefone, :telefone_secundario,
                    :cep, :uf, :cidade, :bairro, :rua, :numero, :create_data
                )
                """
            ),
            {
                "nome": nome,
                "nome_pai": vazio_para_none(payload.get("nome_pai")),
                "nome_mae": vazio_para_none(payload.get("nome_mae")),
                "estado_civil": vazio_para_none(payload.get("estado_civil")),
                "cpf": vazio_para_none(payload.get("cpf")),
                "rg": vazio_para_none(payload.get("rg")),
                "data_nascimento": data_nascimento,
                "idade": calcular_idade(data_nascimento) if data_nascimento else None,
                "alergico": para_bool(payload.get("alergico")),
                "observacao": vazio_para_none(payload.get("observacao")),
                "email": email,
                "telefone": telefone,
                "telefone_secundario": vazio_para_none(payload.get("telefone_secundario")),
                "cep": vazio_para_none(payload.get("cep")),
                "uf": vazio_para_none(payload.get("uf")),
                "cidade": vazio_para_none(payload.get("cidade")),
                "bairro": vazio_para_none(payload.get("bairro")),
                "rua": vazio_para_none(payload.get("rua")),
                "numero": vazio_para_none(payload.get("numero")),
                "create_data": create_data,
            },
        )
        conn.commit()
        return jsonify({"mensagem": "cliente criado com sucesso"}), 201
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "cpf, rg ou email ja cadastrado"}), 409
    except ValueError:
        conn.rollback()
        return jsonify({"error": "data_nascimento invalida"}), 400
    finally:
        conn.close()


@bp.get("/clientes")
@jwt_required()
@role_required(ROLE_ADMIN)
def listar_clientes():
    conn = db.SessionLocal()
    try:
        resultado = conn.execute(text("SELECT * FROM cliente"))
        clientes = [serializar_item(dict(row)) for row in resultado.mappings()]
        return jsonify(clientes), 200
    finally:
        conn.close()


@bp.patch("/clientes/<int:cliente_id>")
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
            campos[chave] = vazio_para_none(payload[chave])

    if "data_nascimento" in campos:
        try:
            campos["idade"] = calcular_idade(campos["data_nascimento"]) if campos["data_nascimento"] else None
        except ValueError:
            return jsonify({"error": "data_nascimento invalida"}), 400

    if "idade" in payload and payload["idade"] is not None and "idade" not in campos:
        campos["idade"] = payload["idade"]

    if "alergico" in payload and payload["alergico"] is not None:
        campos["alergico"] = para_bool(payload["alergico"])

    if not campos:
        return jsonify({"error": "nenhum campo para atualizar"}), 400

    campos["update_data"] = agora_sp()
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
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "cpf, rg ou email ja cadastrado"}), 409
    finally:
        conn.close()
