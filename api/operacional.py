from flask import jsonify, request, Blueprint
from flask_jwt_extended import jwt_required
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from db import SessionLocal
from services.auth_security import ROLE_ADMIN, ROLE_OPERACIONAL, role_required
from services.helpers import agora_sp, normalizar_campo, serializar_item, texto, vazio_para_none

bp = Blueprint("operacional", __name__)


def _campos_patch(data, permitidos):
    return {k: normalizar_campo(data.get(k)) for k in permitidos if k in data}


@bp.get("/api/v1/operacional/consultas")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def listar_consultas():
    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            """
            SELECT consultas.id_consulta, c.nome, retorno, horario, tipo_consulta,
                   status, profissional_responsavel, consultas.observacao
            FROM consultas
            JOIN cliente AS c ON consultas.id_cliente = c.id_cliente
            """
        ))
        consultas = [serializar_item(dict(row)) for row in resultado.mappings()]
        return jsonify(consultas), 200
    finally:
        conn.close()


@bp.get("/api/v1/operacional/<int:id_consulta>/consultas")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def buscar_consulta(id_consulta):
    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            """
            SELECT consultas.id_consulta, c.nome, retorno, horario, tipo_consulta,
                   status, profissional_responsavel, consultas.observacao
            FROM consultas
            JOIN cliente AS c ON consultas.id_cliente = c.id_cliente
            WHERE consultas.id_consulta = :id_consulta
            """
        ), {"id_consulta": id_consulta})
        consulta = resultado.mappings().first()
        if not consulta:
            return jsonify({"error": "consulta nao encontrada"}), 404
        return jsonify(serializar_item(dict(consulta))), 200
    finally:
        conn.close()


@bp.post("/api/v1/operacional/consultas")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def create_consulta():
    payload = request.get_json() or {}

    id_cliente = payload.get("id_cliente")
    profissional_responsavel = texto(payload.get("profissional_responsavel"))
    tipo_consulta = texto(payload.get("tipo_consulta"))
    status = texto(payload.get("status"))
    observacao = vazio_para_none(payload.get("observacao"))
    retorno = texto(payload.get("retorno"))
    horario = texto(payload.get("horario"))
    create_data = agora_sp()

    if not id_cliente or not profissional_responsavel or not tipo_consulta or not retorno or not horario or not status:
        return jsonify({"error": "campos obrigatorios faltantes"}), 400

    conn = SessionLocal()
    try:
        conn.execute(text(
            """
            INSERT INTO consultas (
                id_cliente, profissional_responsavel, tipo_consulta, status,
                observacao, retorno, horario, create_data
            ) VALUES (
                :id_cliente, :profissional_responsavel, :tipo_consulta, :status,
                :observacao, :retorno, :horario, :create_data
            )
            """
        ), {
            "profissional_responsavel": profissional_responsavel,
            "tipo_consulta": tipo_consulta,
            "status": status,
            "observacao": observacao,
            "retorno": retorno,
            "horario": horario,
            "id_cliente": id_cliente,
            "create_data": create_data,
        })
        conn.commit()
        return jsonify({
            "mensagem": "consulta criada",
            "consulta": {
                "profissional_responsavel": profissional_responsavel,
                "tipo_consulta": tipo_consulta,
                "status": status,
                "observacao": observacao,
                "retorno": retorno,
                "horario": horario,
                "id_cliente": id_cliente,
                "create_data": create_data.isoformat(),
            },
        }), 201
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "cliente informado nao existe"}), 400
    finally:
        conn.close()


@bp.patch("/api/v1/operacional/<int:id_consulta>/consultas")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def atualizar_consultas(id_consulta):
    data = request.get_json() or {}
    campos = _campos_patch(data, (
        "profissional_responsavel",
        "tipo_consulta",
        "status",
        "observacao",
        "retorno",
        "horario",
    ))

    if not campos:
        return jsonify({"error": "nenhum item atualizado"}), 400

    campos_atualizar = ", ".join(f"{col} = :{col}" for col in campos)
    parametros = {**campos, "id_consulta": id_consulta, "update_data": agora_sp()}

    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            f"""
            UPDATE consultas
            SET {campos_atualizar},
                update_data = :update_data
            WHERE id_consulta = :id_consulta
            """
        ), parametros)

        if resultado.rowcount == 0:
            return jsonify({"error": "consulta nao encontrada"}), 404

        conn.commit()
        return jsonify({
            "sucesso": "consulta atualizada com sucesso!",
            "consulta": serializar_item({**campos, "update_data": parametros["update_data"]}),
        }), 200
    finally:
        conn.close()


@bp.get("/api/v1/operacional/template")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def listar_mensagens():
    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            "SELECT id_mensagem, titulo, conteudo, create_data, update_data FROM template"
        ))
        templates = [serializar_item(dict(row)) for row in resultado.mappings()]
        return jsonify(templates), 200
    finally:
        conn.close()


@bp.post("/api/v1/operacional/template")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def create_mensagem():
    data = request.get_json() or {}
    titulo = texto(data.get("titulo"))
    conteudo = texto(data.get("conteudo"))
    create_data = agora_sp()

    if not titulo or not conteudo:
        return jsonify({"error": "dados faltantes"}), 400

    conn = SessionLocal()
    try:
        conn.execute(text(
            """
            INSERT INTO template (titulo, conteudo, create_data)
            VALUES (:titulo, :conteudo, :create_data)
            """
        ), {
            "titulo": titulo,
            "conteudo": conteudo,
            "create_data": create_data,
        })
        conn.commit()
        return jsonify({
            "sucesso": "mensagem criada com sucesso!",
            "template": {
                "titulo": titulo,
                "conteudo": conteudo,
                "create_data": create_data.isoformat(),
            },
        }), 201
    finally:
        conn.close()


@bp.patch("/api/v1/operacional/<int:id_mensagem>/template")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def atualizar_mensagem(id_mensagem):
    data = request.get_json() or {}
    campos = _campos_patch(data, ("titulo", "conteudo"))

    if not campos:
        return jsonify({"error": "nenhum campo para atualizar"}), 400

    campos_atualizar = ", ".join(f"{col} = :{col}" for col in campos)
    parametros = {**campos, "id_mensagem": id_mensagem, "update_data": agora_sp()}

    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            f"""
            UPDATE template
            SET {campos_atualizar},
                update_data = :update_data
            WHERE id_mensagem = :id_mensagem
            """
        ), parametros)

        if resultado.rowcount == 0:
            return jsonify({"error": "mensagem nao encontrada"}), 404

        conn.commit()
        return jsonify({
            "mensagem": "mensagem atualizada com sucesso!",
            "template": serializar_item({**campos, "update_data": parametros["update_data"]}),
        }), 200
    finally:
        conn.close()


@bp.delete("/api/v1/operacional/<int:id_mensagem>/template")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def deletar_template(id_mensagem):
    conn = SessionLocal()
    try:
        resultado = conn.execute(
            text("DELETE FROM template WHERE id_mensagem = :id_mensagem"),
            {"id_mensagem": id_mensagem},
        )
        if resultado.rowcount == 0:
            return jsonify({"error": "template nao encontrado"}), 404
        conn.commit()
        return jsonify({"sucesso": "Template excluido com sucesso!"}), 200
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "template vinculado a um lembrete e nao pode ser excluido"}), 409
    finally:
        conn.close()


@bp.get("/api/v1/operacional/lembrete")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def listar_lembretes():
    conn = SessionLocal()
    try:
        resultado = conn.execute(text("SELECT * FROM lembrete"))
        lembretes = [serializar_item(dict(row)) for row in resultado.mappings()]
        return jsonify(lembretes), 200
    finally:
        conn.close()


@bp.post("/api/v1/operacional/lembrete")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def create_lembrete():
    data = request.get_json() or {}

    id_mensagem = data.get("id_mensagem")
    data_disparo = texto(data.get("data_disparo"))
    horario_disparo = texto(data.get("horario_disparo"))
    tipo_disparo = texto(data.get("tipo_disparo"))
    status = texto(data.get("status"))
    create_data = agora_sp()

    if not id_mensagem or not data_disparo or not horario_disparo or not tipo_disparo or not status:
        return jsonify({"error": "campos obrigatorios nao preenchidos"}), 400

    conn = SessionLocal()
    try:
        conn.execute(text(
            """
            INSERT INTO lembrete (
                id_mensagem, data_disparo, horario_disparo, tipo_disparo, status, create_data
            ) VALUES (
                :id_mensagem, :data_disparo, :horario_disparo, :tipo_disparo, :status, :create_data
            )
            """
        ), {
            "id_mensagem": id_mensagem,
            "data_disparo": data_disparo,
            "horario_disparo": horario_disparo,
            "tipo_disparo": tipo_disparo,
            "status": status,
            "create_data": create_data,
        })
        conn.commit()
        return jsonify({
            "mensagem": "lembrete criado com sucesso!",
            "lembrete": {
                "id_mensagem": id_mensagem,
                "data_disparo": data_disparo,
                "horario_disparo": horario_disparo,
                "tipo_disparo": tipo_disparo,
                "status": status,
                "create_data": create_data.isoformat(),
            },
        }), 201
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "template informado nao existe"}), 400
    finally:
        conn.close()


@bp.patch("/api/v1/operacional/<int:id_lembrete>/lembrete")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def atualizar_lembrete(id_lembrete):
    data = request.get_json() or {}
    campos = _campos_patch(data, (
        "id_mensagem",
        "data_disparo",
        "horario_disparo",
        "tipo_disparo",
        "status",
    ))

    if not campos:
        return jsonify({"error": "nenhum item atualizado"}), 400

    campos_atualizar = ", ".join(f"{col} = :{col}" for col in campos)
    parametros = {**campos, "id_lembrete": id_lembrete, "update_data": agora_sp()}

    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            f"""
            UPDATE lembrete
            SET {campos_atualizar},
                update_data = :update_data
            WHERE id_lembrete = :id_lembrete
            """
        ), parametros)

        if resultado.rowcount == 0:
            return jsonify({"error": "lembrete nao encontrado"}), 404

        conn.commit()
        return jsonify({
            "mensagem": "lembrete atualizado com sucesso!",
            "lembrete": serializar_item({**campos, "update_data": parametros["update_data"]}),
        }), 200
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "template informado nao existe"}), 400
    finally:
        conn.close()


@bp.delete("/api/v1/operacional/<int:id_lembrete>/lembrete")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def deletar_lembrete(id_lembrete):
    conn = SessionLocal()
    try:
        resultado = conn.execute(
            text("DELETE FROM lembrete WHERE id_lembrete = :id_lembrete"),
            {"id_lembrete": id_lembrete},
        )
        if resultado.rowcount == 0:
            return jsonify({"error": "lembrete nao encontrado"}), 404
        conn.commit()
        return jsonify({"mensagem": "lembrete excluido com sucesso!"}), 200
    finally:
        conn.close()


@bp.get("/api/v1/operacional/promocoes")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def listar_promocoes():
    conn = SessionLocal()
    try:
        resultado = conn.execute(text("SELECT * FROM promocoes"))
        promocoes = [serializar_item(dict(row)) for row in resultado.mappings()]
        return jsonify({"promocoes": promocoes}), 200
    finally:
        conn.close()


@bp.post("/api/v1/operacional/promocoes")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def create_promocoes():
    data = request.get_json() or {}

    nome = texto(data.get("nome"))
    descricao = texto(data.get("descricao"))
    valor = data.get("valor")
    data_inicio = texto(data.get("data_inicio"))
    data_fim = texto(data.get("data_fim"))
    status = texto(data.get("status"))
    create_data = agora_sp()

    if not nome or not descricao or valor is None or valor == "" or not data_inicio or not data_fim or not status:
        return jsonify({"error": "campos obrigatorios nao preenchidos"}), 400

    conn = SessionLocal()
    try:
        conn.execute(text(
            """
            INSERT INTO promocoes (
                nome, descricao, valor, data_inicio, data_fim, status, create_data
            ) VALUES (
                :nome, :descricao, :valor, :data_inicio, :data_fim, :status, :create_data
            )
            """
        ), {
            "nome": nome,
            "descricao": descricao,
            "valor": valor,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "status": status,
            "create_data": create_data,
        })
        conn.commit()
        return jsonify({
            "mensagem": "promocao criada com sucesso!",
            "promocao": {
                "nome": nome,
                "descricao": descricao,
                "valor": valor,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "status": status,
                "create_data": create_data.isoformat(),
            },
        }), 201
    finally:
        conn.close()


@bp.patch("/api/v1/operacional/<int:id_promocao>/promocoes")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def atualizar_promocoes(id_promocao):
    data = request.get_json() or {}
    campos = _campos_patch(data, (
        "nome",
        "descricao",
        "valor",
        "data_inicio",
        "data_fim",
        "status",
    ))

    if not campos:
        return jsonify({"error": "nenhum item atualizado"}), 400

    campos_atualizar = ", ".join(f"{col} = :{col}" for col in campos)
    parametros = {**campos, "id_promocao": id_promocao, "update_data": agora_sp()}

    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            f"""
            UPDATE promocoes
            SET {campos_atualizar},
                update_data = :update_data
            WHERE id_promocao = :id_promocao
            """
        ), parametros)

        if resultado.rowcount == 0:
            return jsonify({"error": "promocao nao encontrada"}), 404

        conn.commit()
        return jsonify({
            "mensagem": "promocao atualizada com sucesso!",
            "promocao": serializar_item({**campos, "update_data": parametros["update_data"]}),
        }), 200
    finally:
        conn.close()
