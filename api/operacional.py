from flask import jsonify, request, Blueprint
from flask_jwt_extended import jwt_required
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from db import SessionLocal
from services.auth_security import ROLE_ADMIN, ROLE_OPERACIONAL, clinica_id_do_token, role_required
from services.helpers import agora_sp, normalizar_campo, serializar_item, texto, vazio_para_none

bp = Blueprint("operacional", __name__, url_prefix="/api/v1/operacional")


def _campos_patch(data, permitidos):
    return {k: normalizar_campo(data.get(k)) for k in permitidos if k in data}


def _id_clinica_ou_erro():
    try:
        return clinica_id_do_token(), None
    except (TypeError, ValueError):
        return None, (jsonify({"error": "token invalido"}), 401)


@bp.get("/consultas")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def listar_consultas():
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            """
            SELECT consultas.id_consulta, consultas.id_cliente, c.nome, retorno, horario,
                   tipo_consulta, status, profissional_responsavel, consultas.observacao,
                   consultas.create_data, consultas.update_data
            FROM consultas
            JOIN cliente AS c ON consultas.id_cliente = c.id_cliente
            WHERE consultas.id_clinica = :id_clinica
            ORDER BY retorno DESC, horario DESC
            """
        ), {"id_clinica": id_clinica})
        consultas = [serializar_item(dict(row)) for row in resultado.mappings()]
        return jsonify(consultas), 200
    finally:
        conn.close()


@bp.get("/consultas/<int:id_consulta>")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def buscar_consulta(id_consulta):
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            """
            SELECT consultas.id_consulta, consultas.id_cliente, c.nome, retorno, horario,
                   tipo_consulta, status, profissional_responsavel, consultas.observacao,
                   consultas.create_data, consultas.update_data
            FROM consultas
            JOIN cliente AS c ON consultas.id_cliente = c.id_cliente
            WHERE consultas.id_consulta = :id_consulta
              AND consultas.id_clinica = :id_clinica
            """
        ), {"id_consulta": id_consulta, "id_clinica": id_clinica})
        consulta = resultado.mappings().first()
        if not consulta:
            return jsonify({"error": "consulta nao encontrada"}), 404
        return jsonify(serializar_item(dict(consulta))), 200
    finally:
        conn.close()


@bp.post("/consultas")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def create_consulta():
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

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
        cliente = conn.execute(
            text(
                "SELECT id_cliente FROM cliente "
                "WHERE id_cliente = :id_cliente AND id_clinica = :id_clinica"
            ),
            {"id_cliente": id_cliente, "id_clinica": id_clinica},
        ).first()
        if not cliente:
            return jsonify({"error": "cliente informado nao existe"}), 400

        conn.execute(text(
            """
            INSERT INTO consultas (
                id_cliente, id_clinica, profissional_responsavel, tipo_consulta, status,
                observacao, retorno, horario, create_data
            ) VALUES (
                :id_cliente, :id_clinica, :profissional_responsavel, :tipo_consulta, :status,
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
            "id_clinica": id_clinica,
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
                "id_clinica": id_clinica,
                "create_data": create_data.isoformat(),
            },
        }), 201
    except IntegrityError:
        conn.rollback()
        return jsonify({"error": "cliente informado nao existe"}), 400
    finally:
        conn.close()


@bp.patch("/consultas/<int:id_consulta>")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def atualizar_consultas(id_consulta):
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

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
    parametros = {
        **campos,
        "id_consulta": id_consulta,
        "id_clinica": id_clinica,
        "update_data": agora_sp(),
    }

    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            f"""
            UPDATE consultas
            SET {campos_atualizar},
                update_data = :update_data
            WHERE id_consulta = :id_consulta
              AND id_clinica = :id_clinica
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


@bp.get("/templates")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def listar_mensagens():
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            """
            SELECT id_mensagem, titulo, conteudo, create_data, update_data
            FROM template
            WHERE id_clinica = :id_clinica
            ORDER BY id_mensagem DESC
            """
        ), {"id_clinica": id_clinica})
        templates = [serializar_item(dict(row)) for row in resultado.mappings()]
        return jsonify(templates), 200
    finally:
        conn.close()


@bp.post("/templates")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def create_mensagem():
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

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
            INSERT INTO template (id_clinica, titulo, conteudo, create_data)
            VALUES (:id_clinica, :titulo, :conteudo, :create_data)
            """
        ), {
            "id_clinica": id_clinica,
            "titulo": titulo,
            "conteudo": conteudo,
            "create_data": create_data,
        })
        conn.commit()
        return jsonify({
            "sucesso": "mensagem criada com sucesso!",
            "template": {
                "id_clinica": id_clinica,
                "titulo": titulo,
                "conteudo": conteudo,
                "create_data": create_data.isoformat(),
            },
        }), 201
    finally:
        conn.close()


@bp.patch("/templates/<int:id_mensagem>")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def atualizar_mensagem(id_mensagem):
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

    data = request.get_json() or {}
    campos = _campos_patch(data, ("titulo", "conteudo"))

    if not campos:
        return jsonify({"error": "nenhum campo para atualizar"}), 400

    campos_atualizar = ", ".join(f"{col} = :{col}" for col in campos)
    parametros = {
        **campos,
        "id_mensagem": id_mensagem,
        "id_clinica": id_clinica,
        "update_data": agora_sp(),
    }

    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            f"""
            UPDATE template
            SET {campos_atualizar},
                update_data = :update_data
            WHERE id_mensagem = :id_mensagem
              AND id_clinica = :id_clinica
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


@bp.delete("/templates/<int:id_mensagem>")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def deletar_template(id_mensagem):
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

    conn = SessionLocal()
    try:
        resultado = conn.execute(
            text(
                "DELETE FROM template "
                "WHERE id_mensagem = :id_mensagem AND id_clinica = :id_clinica"
            ),
            {"id_mensagem": id_mensagem, "id_clinica": id_clinica},
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


@bp.get("/lembretes")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def listar_lembretes():
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

    conn = SessionLocal()
    try:
        resultado = conn.execute(
            text(
                """
                SELECT l.id_lembrete, l.id_mensagem, t.titulo AS template_titulo,
                       l.data_disparo, l.horario_disparo, l.tipo_disparo, l.status,
                       l.create_data, l.update_data
                FROM lembrete AS l
                LEFT JOIN template AS t ON t.id_mensagem = l.id_mensagem
                WHERE l.id_clinica = :id_clinica
                ORDER BY l.data_disparo DESC, l.horario_disparo DESC
                """
            ),
            {"id_clinica": id_clinica},
        )
        lembretes = [serializar_item(dict(row)) for row in resultado.mappings()]
        return jsonify(lembretes), 200
    finally:
        conn.close()


@bp.post("/lembretes")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def create_lembrete():
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

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
        template = conn.execute(
            text(
                "SELECT id_mensagem FROM template "
                "WHERE id_mensagem = :id_mensagem AND id_clinica = :id_clinica"
            ),
            {"id_mensagem": id_mensagem, "id_clinica": id_clinica},
        ).first()
        if not template:
            return jsonify({"error": "template informado nao existe"}), 400

        conn.execute(text(
            """
            INSERT INTO lembrete (
                id_mensagem, id_clinica, data_disparo, horario_disparo, tipo_disparo, status, create_data
            ) VALUES (
                :id_mensagem, :id_clinica, :data_disparo, :horario_disparo, :tipo_disparo, :status, :create_data
            )
            """
        ), {
            "id_mensagem": id_mensagem,
            "id_clinica": id_clinica,
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
                "id_clinica": id_clinica,
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


@bp.patch("/lembretes/<int:id_lembrete>")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def atualizar_lembrete(id_lembrete):
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

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

    conn = SessionLocal()
    try:
        if "id_mensagem" in campos:
            template = conn.execute(
                text(
                    "SELECT id_mensagem FROM template "
                    "WHERE id_mensagem = :id_mensagem AND id_clinica = :id_clinica"
                ),
                {"id_mensagem": campos["id_mensagem"], "id_clinica": id_clinica},
            ).first()
            if not template:
                return jsonify({"error": "template informado nao existe"}), 400

        campos_atualizar = ", ".join(f"{col} = :{col}" for col in campos)
        parametros = {
            **campos,
            "id_lembrete": id_lembrete,
            "id_clinica": id_clinica,
            "update_data": agora_sp(),
        }

        resultado = conn.execute(text(
            f"""
            UPDATE lembrete
            SET {campos_atualizar},
                update_data = :update_data
            WHERE id_lembrete = :id_lembrete
              AND id_clinica = :id_clinica
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


@bp.delete("/lembretes/<int:id_lembrete>")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def deletar_lembrete(id_lembrete):
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

    conn = SessionLocal()
    try:
        resultado = conn.execute(
            text(
                "DELETE FROM lembrete "
                "WHERE id_lembrete = :id_lembrete AND id_clinica = :id_clinica"
            ),
            {"id_lembrete": id_lembrete, "id_clinica": id_clinica},
        )
        if resultado.rowcount == 0:
            return jsonify({"error": "lembrete nao encontrado"}), 404
        conn.commit()
        return jsonify({"mensagem": "lembrete excluido com sucesso!"}), 200
    finally:
        conn.close()


@bp.get("/promocoes")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def listar_promocoes():
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

    conn = SessionLocal()
    try:
        resultado = conn.execute(
            text(
                """
                SELECT id_promocao, nome, descricao, valor, data_inicio, data_fim, status,
                       create_data, update_data
                FROM promocoes
                WHERE id_clinica = :id_clinica
                ORDER BY data_inicio DESC
                """
            ),
            {"id_clinica": id_clinica},
        )
        promocoes = [serializar_item(dict(row)) for row in resultado.mappings()]
        return jsonify({"promocoes": promocoes}), 200
    finally:
        conn.close()


@bp.post("/promocoes")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def create_promocoes():
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

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
                id_clinica, nome, descricao, valor, data_inicio, data_fim, status, create_data
            ) VALUES (
                :id_clinica, :nome, :descricao, :valor, :data_inicio, :data_fim, :status, :create_data
            )
            """
        ), {
            "id_clinica": id_clinica,
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
                "id_clinica": id_clinica,
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


@bp.patch("/promocoes/<int:id_promocao>")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def atualizar_promocoes(id_promocao):
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

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
    parametros = {
        **campos,
        "id_promocao": id_promocao,
        "id_clinica": id_clinica,
        "update_data": agora_sp(),
    }

    conn = SessionLocal()
    try:
        resultado = conn.execute(text(
            f"""
            UPDATE promocoes
            SET {campos_atualizar},
                update_data = :update_data
            WHERE id_promocao = :id_promocao
              AND id_clinica = :id_clinica
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


@bp.delete("/promocoes/<int:id_promocao>")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def deletar_promocao(id_promocao):
    id_clinica, erro = _id_clinica_ou_erro()
    if erro:
        return erro

    conn = SessionLocal()
    try:
        resultado = conn.execute(
            text(
                "DELETE FROM promocoes "
                "WHERE id_promocao = :id_promocao AND id_clinica = :id_clinica"
            ),
            {"id_promocao": id_promocao, "id_clinica": id_clinica},
        )
        if resultado.rowcount == 0:
            return jsonify({"error": "promocao nao encontrada"}), 404

        conn.commit()
        return jsonify({"mensagem": "promocao excluida com sucesso!"}), 200
    finally:
        conn.close()
