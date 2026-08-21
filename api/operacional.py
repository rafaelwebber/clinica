from datetime import date, datetime
from flask import Flask, jsonify, request, Blueprint
from flask_jwt_extended import jwt_required
from sqlalchemy import text
from db import SessionLocal
from services.helpers import buscar_id
from services.auth_security import ROLE_ADMIN, ROLE_OPERACIONAL, role_required

bp = Blueprint("operacional", __name__)


@bp.get("/api/v1/operacional/consultas")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def listar_consultas():
    conn = SessionLocal()

    try:
        resultado = conn.execute(text(
            """
                SELECT c.nome, retorno, horario, tipo_consulta, status, profissional_responsavel FROM consultas JOIN cliente AS c ON consultas.id_cliente = c.id_cliente
            """
        ))
        consultas = []

        for row in resultado.mappings():
            item = dict(row)
            if item.get("horario"):
                item["horario"] = str(item["horario"])
            if item.get("retorno"):
                item["retorno"] = item["retorno"].isoformat()
            consultas.append(item)

        

        if not consultas:
            return jsonify({"error": "nenhuma consulta encontrada"}),404

        return jsonify(consultas)    
    finally:
        conn.close()
        
@bp.post("/api/v1/operacional/consultas")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def create_consulta():
    
    payload = request.get_json() or {}

    id_cliente = payload.get("id_cliente")
    profissional_responsavel = payload.get("profissional_responsavel")
    tipo_consulta = payload.get("tipo_consulta")
    status = payload.get("status")
    observacao = payload.get("observacao")
    retorno = payload.get("retorno") #data de retorno 
    horario = payload.get("horario")
    create_data = datetime.now()

    if not profissional_responsavel or not tipo_consulta or not retorno or not horario or not status:
        return jsonify({"error": "campos obrigatorios faltantes"}), 400

    try:
        conn = SessionLocal()
        conn.execute(text(
            """
                INSERT INTO consultas (id_cliente ,profissional_responsavel, tipo_consulta, status, observacao, retorno, horario, create_data)VALUES(:id_cliente, :profissional_responsavel, :tipo_consulta, :status, :observacao, :retorno, :horario, :create_data)
            """
                ),
                {
            "profissional_responsavel": profissional_responsavel,
            "tipo_consulta":tipo_consulta,
            "status": status,
            "observacao": observacao,
            "retorno": retorno,
            "horario": horario,
            "id_cliente": id_cliente,
            "create_data" : create_data
                },)
        
        conn.commit()
        return jsonify({"mensagem":"consulta criada",
        "consulta": {
            "profissional_responsavel": profissional_responsavel,
            "tipo_consulta":tipo_consulta,
            "status": status,
            "observacao": observacao,
            "retorno": retorno,
            "horario": horario,
            "id_cliente": id_cliente,
            "create_data" : create_data
        }}), 201
    finally:
        conn.close()

@bp.patch("/api/v1/operacional/<int:id_consulta>/consultas")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def atualizar_consultas(id_consulta):
    data = request.get_json() or {}
 
    atualizar = (
        "profissional_responsavel",
        "tipo_consulta",
        "status",
        "observacao",
        "retorno",
        "horario",
    )
    campos = {k: data.get(k) for k in atualizar if k in data}
 
 
    if not campos:
        return jsonify({"error": "nenhum item atualizado"}), 400

    campos_atualizar = ", ".join(f"{col} = :{col}" for col in campos) 
    parametros = {**campos, "id_consulta": id_consulta, "update_data" :datetime.now()}
    
    try:
        conn = SessionLocal()
        resultado = conn.execute(text(
            f"""
                UPDATE consultas
                SET {campos_atualizar},
                update_data = :update_data
                WHERE id_consulta = :id_consulta
            """
        ),
        parametros)

        if resultado.rowcount == 0:
            return jsonify({"error": "consulta nao encontrada"}),404
    
        conn.commit()
        return jsonify({"sucesso": "consulta atualizada com sucesso!",
        "consulta": {
            **campos
            }
        }), 200


    finally:
        conn.close()

@bp.get("/api/v1/operacional/template")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def listar_mensagens():
    conn= SessionLocal()

    try:   
        resultado = conn.execute(text(
            """ 
                SELECT titulo, conteudo, update_data FROM template;
            """
        ))

        consulta = [dict(row) for row in resultado.mappings()]
        if not consulta:
            return jsonify({"erro": "nenhuma mensagem cadastrada"}), 404

        return jsonify(consulta)

    finally:
        conn.close()

@bp.post("/api/v1/operacional/template")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def create_mensagem():
    data = request.get_json() or {}

    titulo = data.get("titulo")
    conteudo = data.get("conteudo")
    create_data = datetime.now()

    conn = SessionLocal()
    try:
        if not titulo or not conteudo: 
            return jsonify({"error": "dados faltantes"}), 400

        

        resultado = conn.execute(text(
            """
                INSERT INTO template (titulo, conteudo, create_data) 
                VALUES(:titulo, :conteudo, :create_data);
            """
        ),
        {
            "titulo" : titulo,
            "conteudo" : conteudo,
            "create_data" : create_data
        },
        )
        conn.commit()
        return jsonify({"sucesso": "mensagem criada com sucesso!",
        "template": {
            "titulo": titulo,
            "conteudo": conteudo,
            "create_data": create_data.isoformat()
        }}), 201


    finally:
        conn.close()
    
@bp.patch("/api/v1/operacional/<int:id_mensagem>/template")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def atualizar_mensagem(id_mensagem):
    data = request.get_json() or {}

    titulo = data.get("titulo")
    conteudo = data.get("conteudo")  
    update_data = datetime.now()

    try:
        conn = SessionLocal()
        if titulo is not None:
            resultados =conn.execute(text(
            """
                UPDATE template 
                SET titulo = :titulo,
                update_data = :update_data
                WHERE id_mensagem = :id_mensagem
            """
        ),
        {
            "titulo": titulo,
            "id_mensagem": id_mensagem,
            "update_data": update_data
        })
        if conteudo is not None:
          resultados = conn.execute(text(
            """
                UPDATE template 
                SET conteudo = :conteudo, 
                update_data = :update_data
                WHERE id_mensagem = :id_mensagem
            """
        ),
        {
            "conteudo": conteudo,
            "id_mensagem": id_mensagem,
            "update_data": update_data
        })
        if resultados.rowcount == 0:
            return jsonify({"error": "mensagem nao encontrada"}), 404
        
        if titulo is None and conteudo is None:
            return jsonify({"error": "nenhum campo para atualizar"}), 400 

        conn.commit()
        return jsonify({"mensagem": "mensagem atualizada com sucesso!",
        "template": {
            "titulo": titulo,
            "conteudo": conteudo,
            "update_data": update_data
        }}), 200
         
    finally:
        conn.close()

@bp.delete("/api/v1/operacional/<int:id_mensagem>/template")
@jwt_required()
@role_required(ROLE_ADMIN, ROLE_OPERACIONAL)
def deletar_template(id_mensagem):
    try:
        conn = SessionLocal()
        conn.execute(text(
            f"""DELETE FROM template
            WHERE id_mensagem = {id_mensagem}"""
        ))
        conn.commit()
        return jsonify({"sucesso": "Template excluido com sucesso!"}), 200
    finally:
        conn.close()
    
    

