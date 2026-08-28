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
from werkzeug.security import generate_password_hash
import db
from services.auth_security import (
    MSG_CREDENCIAIS_INVALIDAS,
    MSG_DADOS_INCOMPLETOS,
    MSG_MUITAS_TENTATIVAS,
    ROLE_ADMIN,
    ROLE_OPERACIONAL,
    clinica_id_do_token,
    cnpj_valido,
    limpar_falhas_login,
    login_bloqueado,
    normalizar_cnpj,
    registrar_falha_login,
    revogar_token,
    role_required,
    senha_confere,
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


def _resposta_bloqueio(segundos: int):
    resp = jsonify({"error": MSG_MUITAS_TENTATIVAS})
    resp.status_code = 429
    resp.headers["Retry-After"] = str(max(1, int(segundos)))
    return resp


def _resposta_credenciais_invalidas():
    return jsonify({"error": MSG_CREDENCIAIS_INVALIDAS}), 401


def _buscar_usuarios_por_email(conn, email: str):
    return conn.execute(
        text(
            """
            SELECT u.usuario_id, u.role_id, u.senha, u.id_clinica
            FROM usuarios u
            INNER JOIN clinicas c ON c.id_clinica = u.id_clinica
            WHERE u.email = :email
              AND (c.status IS NULL OR c.status = 'ativo')
            ORDER BY u.usuario_id ASC
            """
        ),
        {"email": email},
    ).mappings().all()


def _buscar_clinica_por_email(conn, email: str):
    return conn.execute(
        text(
            """
            SELECT id_clinica, senha
            FROM clinicas
            WHERE LOWER(email) = :email
              AND (status IS NULL OR status = 'ativo')
            ORDER BY id_clinica ASC
            """
        ),
        {"email": email},
    ).mappings().all()


def _buscar_usuarios_por_cnpj(conn, cnpj: str):
    return conn.execute(
        text(
            """
            SELECT u.usuario_id, u.role_id, u.senha, u.id_clinica
            FROM usuarios u
            INNER JOIN clinicas c ON c.id_clinica = u.id_clinica
            WHERE c.cnpj = :cnpj
              AND u.role_id = :role_admin
              AND (c.status IS NULL OR c.status = 'ativo')
            ORDER BY u.usuario_id ASC
            """
        ),
        {"cnpj": cnpj, "role_admin": ROLE_ADMIN},
    ).mappings().all()


def _buscar_clinica_por_cnpj(conn, cnpj: str):
    return conn.execute(
        text(
            """
            SELECT id_clinica, senha
            FROM clinicas
            WHERE cnpj = :cnpj
              AND (status IS NULL OR status = 'ativo')
            ORDER BY id_clinica ASC
            """
        ),
        {"cnpj": cnpj},
    ).mappings().all()


def _candidatos_login(conn, usar_email: bool, email: str, cnpj: str):
    candidatos = []
    if usar_email:
        for row in _buscar_usuarios_por_email(conn, email):
            candidatos.append({"tipo": "usuario", **dict(row)})
        for row in _buscar_clinica_por_email(conn, email):
            candidatos.append({"tipo": "clinica", **dict(row)})
    else:
        for row in _buscar_usuarios_por_cnpj(conn, cnpj):
            candidatos.append({"tipo": "usuario", **dict(row)})
        for row in _buscar_clinica_por_cnpj(conn, cnpj):
            candidatos.append({"tipo": "clinica", **dict(row)})
    return candidatos


def _autenticar_candidatos(candidatos, senha: str):
    for candidato in candidatos:
        if not senha_confere(candidato.get("senha"), senha):
            continue
        if candidato["tipo"] == "usuario":
            return {
                "identity": str(candidato["usuario_id"]),
                "claims": {
                    "role_id": int(candidato["role_id"]),
                    "clinica_id": int(candidato["id_clinica"]),
                },
            }
        return {
            "identity": f"clinica:{candidato['id_clinica']}",
            "claims": {
                "role_id": ROLE_ADMIN,
                "clinica_id": int(candidato["id_clinica"]),
            },
        }
    senha_confere(None, senha)
    return None


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = texto(data.get("email")).lower()
    senha = texto(data.get("senha"))
    cnpj = normalizar_cnpj(texto(data.get("cnpj")))
    ip = request.remote_addr or "unknown"

    # Aceita email OU cnpj (+ senha). Se ambos vierem, prioriza email.
    usar_email = bool(email)
    usar_cnpj = bool(cnpj) and not usar_email

    if not senha or (not usar_email and not usar_cnpj):
        if email or cnpj or senha:
            identificador = email or cnpj or "vazio"
            ficou_bloqueado, lock_segundos = registrar_falha_login(ip, identificador)
            if ficou_bloqueado:
                return _resposta_bloqueio(lock_segundos)
        return jsonify({"error": MSG_DADOS_INCOMPLETOS}), 400

    if usar_cnpj and not cnpj_valido(cnpj):
        ficou_bloqueado, lock_segundos = registrar_falha_login(ip, cnpj)
        if ficou_bloqueado:
            return _resposta_bloqueio(lock_segundos)
        return _resposta_credenciais_invalidas()

    identificador = email if usar_email else cnpj

    bloqueado, segundos = login_bloqueado(ip, identificador)
    if bloqueado:
        return _resposta_bloqueio(segundos)

    conn = db.SessionLocal()
    try:
        candidatos = _candidatos_login(conn, usar_email, email, cnpj)
        auth = _autenticar_candidatos(candidatos, senha)
        if auth is None:
            ficou_bloqueado, lock_segundos = registrar_falha_login(ip, identificador)
            if ficou_bloqueado:
                return _resposta_bloqueio(lock_segundos)
            return _resposta_credenciais_invalidas()

        limpar_falhas_login(ip, identificador)
        access = create_access_token(
            identity=auth["identity"],
            additional_claims=auth["claims"],
        )
        refresh = create_refresh_token(
            identity=auth["identity"],
            additional_claims=auth["claims"],
        )

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
    jwt_data = get_jwt()
    try:
        claims = {
            "role_id": int(jwt_data.get("role_id")),
            "clinica_id": int(jwt_data.get("clinica_id")),
        }
    except (TypeError, ValueError):
        return jsonify({"error": "token invalido"}), 401
    revogar_token(jwt_data["jti"])
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


@bp.get("/perfil")
@jwt_required()
def perfil():
    identidade = get_jwt_identity() or ""
    try:
        id_clinica = clinica_id_do_token()
        role_id = int(get_jwt().get("role_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "token invalido"}), 401

    conn = db.SessionLocal()
    try:
        clinica = conn.execute(
            text("SELECT nome, cidade, uf FROM clinicas WHERE id_clinica = :id_clinica"),
            {"id_clinica": id_clinica},
        ).mappings().first()

        resposta = {
            "role_id": role_id,
            "clinica": dict(clinica) if clinica else None,
        }

        if identidade.startswith("clinica:"):
            resposta["tipo"] = "clinica"
            resposta["nome"] = clinica["nome"] if clinica else "Clinica"
            return jsonify(resposta), 200

        usuario = conn.execute(
            text(
                "SELECT nome, email FROM usuarios "
                "WHERE usuario_id = :usuario_id AND id_clinica = :id_clinica"
            ),
            {"usuario_id": identidade, "id_clinica": id_clinica},
        ).mappings().first()
        if not usuario:
            return jsonify({"error": "usuario nao encontrado"}), 404

        resposta["tipo"] = "usuario"
        resposta["nome"] = usuario["nome"]
        resposta["email"] = usuario["email"]
        return jsonify(resposta), 200
    finally:
        conn.close()


@bp.get("/usuarios")
@jwt_required()
@role_required(ROLE_ADMIN)
def listar_usuario():
    try:
        id_clinica = clinica_id_do_token()
    except (TypeError, ValueError):
        return jsonify({"error": "token invalido"}), 401

    conn = db.SessionLocal()
    try:
        resultado = conn.execute(text(
            """
            SELECT usuario_id, nome, role_id, cpf, rg, data_nascimento, email,
                   telefone, telefone_secundario, create_data, update_data
            FROM usuarios
            WHERE id_clinica = :id_clinica
            ORDER BY nome ASC
            """
        ), {"id_clinica": id_clinica})
        usuarios = [serializar_item(dict(row)) for row in resultado.mappings()]
        return jsonify(usuarios), 200
    finally:
        conn.close()


@bp.post("/usuarios")
@jwt_required()
@role_required(ROLE_ADMIN)
def create_usuario():
    try:
        id_clinica = clinica_id_do_token()
    except (TypeError, ValueError):
        return jsonify({"error": "token invalido"}), 401

    payload = request.get_json() or {}
    nome = texto(payload.get("nome"))
    cpf = texto(payload.get("cpf"))
    rg = vazio_para_none(payload.get("rg"))
    data_nascimento = vazio_para_none(payload.get("data_nascimento"))
    email = texto(payload.get("email")).lower()
    telefone = vazio_para_none(payload.get("telefone"))
    telefone_secundario = vazio_para_none(payload.get("telefone_secundario"))
    senha = texto(payload.get("senha"))
    create_data = agora_sp()

    try:
        role_id = int(payload.get("role_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "role_id invalido"}), 400

    if role_id not in (ROLE_ADMIN, ROLE_OPERACIONAL):
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
                    (nome, role_id, id_clinica, cpf, rg, data_nascimento, email, telefone,
                     telefone_secundario, senha, create_data)
                VALUES (:nome, :role_id, :id_clinica, :cpf, :rg, :data_nascimento, :email,
                        :telefone, :telefone_secundario, :senha, :create_data)
                """
            ),
            {
                "nome": nome,
                "role_id": role_id,
                "id_clinica": id_clinica,
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
    try:
        id_clinica = clinica_id_do_token()
    except (TypeError, ValueError):
        return jsonify({"error": "token invalido"}), 401

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

    if campos.get("email"):
        campos["email"] = campos["email"].lower()

    if "role_id" in payload and payload["role_id"] is not None:
        try:
            role_id = int(payload["role_id"])
        except (TypeError, ValueError):
            return jsonify({"error": "role_id invalido"}), 400
        if role_id not in (ROLE_ADMIN, ROLE_OPERACIONAL):
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
    campos["id_clinica"] = id_clinica

    conn = db.SessionLocal()
    try:
        resultado = conn.execute(
            text(
                f"UPDATE usuarios SET {sets} "
                "WHERE usuario_id = :user_id AND id_clinica = :id_clinica"
            ),
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
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def create_cliente():
    try:
        id_clinica = clinica_id_do_token()
    except (TypeError, ValueError):
        return jsonify({"error": "token invalido"}), 401

    payload = request.get_json() or {}

    nome = texto(payload.get("nome"))
    email = texto(payload.get("email")).lower()
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
                    id_clinica, nome, nome_pai, nome_mae, estado_civil, cpf, rg, data_nascimento,
                    idade, alergico, observacao, email, telefone, telefone_secundario,
                    cep, uf, cidade, bairro, rua, numero, create_data
                ) VALUES (
                    :id_clinica, :nome, :nome_pai, :nome_mae, :estado_civil, :cpf, :rg, :data_nascimento,
                    :idade, :alergico, :observacao, :email, :telefone, :telefone_secundario,
                    :cep, :uf, :cidade, :bairro, :rua, :numero, :create_data
                )
                """
            ),
            {
                "id_clinica": id_clinica,
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
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def listar_clientes():
    try:
        id_clinica = clinica_id_do_token()
    except (TypeError, ValueError):
        return jsonify({"error": "token invalido"}), 401

    conn = db.SessionLocal()
    try:
        resultado = conn.execute(
            text(
                """
                SELECT id_cliente, nome, nome_pai, nome_mae, estado_civil, cpf, rg,
                       data_nascimento, idade, alergico, observacao, email, telefone,
                       telefone_secundario, cep, uf, cidade, bairro, rua, numero,
                       create_data, update_data
                FROM cliente
                WHERE id_clinica = :id_clinica
                ORDER BY nome ASC
                """
            ),
            {"id_clinica": id_clinica},
        )
        clientes = [serializar_item(dict(row)) for row in resultado.mappings()]
        return jsonify(clientes), 200
    finally:
        conn.close()


@bp.patch("/clientes/<int:cliente_id>")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def update_cliente(cliente_id):
    try:
        id_clinica = clinica_id_do_token()
    except (TypeError, ValueError):
        return jsonify({"error": "token invalido"}), 401

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

    if campos.get("email"):
        campos["email"] = campos["email"].lower()

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
    campos["id_clinica"] = id_clinica

    conn = db.SessionLocal()
    try:
        resultado = conn.execute(
            text(
                f"UPDATE cliente SET {sets} "
                "WHERE id_cliente = :cliente_id AND id_clinica = :id_clinica"
            ),
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


@bp.post("/clinicas")
def create_clinica():
    data = request.get_json() or {}
    nome = texto(data.get("nome"))
    cnpj = normalizar_cnpj(texto(data.get("cnpj")))
    email = texto(data.get("email")).lower()
    senha = texto(data.get("senha"))
    telefone = vazio_para_none(data.get("telefone"))
    cep = texto(data.get("cep"))
    uf = texto(data.get("uf")).upper()
    cidade = texto(data.get("cidade"))
    bairro = texto(data.get("bairro"))
    rua = texto(data.get("rua"))
    numero = texto(data.get("numero"))
    complemento = vazio_para_none(data.get("complemento"))
    status = "ativo"
    create_data = agora_sp()

    if not nome or not cnpj or not email or not cep or not uf or not cidade or not bairro or not rua or not numero or not senha:
        return jsonify({"error": "campos obrigatorios"}), 400

    if not cnpj_valido(cnpj):
        return jsonify({"error": "cnpj invalido"}), 400

    if not validar_senha(senha):
        return jsonify({
            "error": (
                "senha tem que conter pelo menos 8 caracteres, uma letra maiuscula, "
                "uma letra minuscula, um numero e um caracter especial"
            )
        }), 400

    conn = db.SessionLocal()
    try:
        conn.execute(text(
            """
            INSERT INTO clinicas (nome, cnpj, email, telefone, cep, uf, cidade, bairro, rua, numero, complemento, status, create_data, senha)
            VALUES (:nome, :cnpj, :email, :telefone, :cep, :uf, :cidade, :bairro, :rua, :numero, :complemento, :status, :create_data, :senha)
            """
        ),{
            "nome": nome,
            "cnpj": cnpj,
            "telefone": telefone,
            "email": email,
            "cep": cep,
            "uf": uf,
            "cidade": cidade,
            "bairro": bairro,
            "rua": rua,
            "numero": numero,
            "complemento": complemento,
            "status": status,
            "create_data": create_data,
            "senha": generate_password_hash(senha)
        })
        conn.commit()
        return jsonify({"mensagem": "clinica criada com sucesso!"}), 201
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "cnpj ou email ja cadastrado"}), 409
    finally:
        conn.close()

