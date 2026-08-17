from datetime import date, datetime
from flask import Flask, jsonify, request, Blueprint
from sqlalchemy import text
from db import SessionLocal
from services.helpers import buscar_id

bp = Blueprint("operacional", __name__)


@bp.get("/api/v1/operacional/consultas")
def listar_consultas():
    conn = SessionLocal()

    try:
        resultado = conn.execute(text(
            """
                SELECT c.nome, retorno, horario, tipo_consulta, status FROM consultas JOIN cliente AS c ON consultas.id_cliente = c.id_cliente
            """
        ))
        consultas = [dict(row) for row in resultado.mappings()]
        
        if not consultas:
            return jsonify({"error": "nenhuma consulta encontrada"}),404

        return jsonify (consultas)

    finally:
        conn.close()

@bp.post("/api/v1/operacional/consultas")
def create_consulta():
    
    payload = request.get_json() or {}

    id_cliente = payload.get("id_cliente")
    profissional_responsavel = payload.get("profissional_responsavel")
    tipo_consulta = payload.get("tipo_consulta")
    status = payload.get("status")
    observacao = payload.get("observacao")
    retorno = payload.get("retorno")
    horario = payload.get("horario")
    create_data = datetime.now()

    if not profissional_responsavel or not tipo_consulta or not retorno or not horario:
        return jsonify({"error": "campos obrigatorios faltantes"})

    try:
        conn = SessionLocal()
        conn.execute(text(
            """
                INSERT INTO consultas (id_cliente ,profissional_responsavel, tipo_consulta, status, observacao, retorno, horario)VALUES(:id_cliente, :profissional_responsavel, :tipo_consulta, :status, :observacao, :retorno, :horario)
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
        return jsonify({"mensagem":"consulta criada"}), 201
    finally:
        conn.close()

@bp.get("/api/v1/operacional/template")
def listar_mensagens():
    conn= SessionLocal()

    try:   
        resultado = conn.execute(
            """ 
                SELECT titulo, conteudo FROM template;
            """
        )

        consulta = [dict(row) for row in resultado.mappings()]
        if not consulta:
            return jsonify({"erro": "nenhuma mensagem cadastrada"})

        return jsonify(consulta)

    finally:
        conn.close()

@bp.post("/api/v1/operacional/template")
def create_mensagem():
    data = request.get_json() or {}

    titulo = data.get("titulo")
    conteudo = data.get("conteudo")
    create_data = datetime.now()

    try:
        if not titulo or not conteudo: 
            return jsonify({"error": "dados faltantes"})

        conn = SessionLocal()

        conn.execute(text(
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
        return jsonify({"mensagem": "mensagem criada com sucesso!"}), 201


    finally:
        conn.close()

    
@bp.patch("/api/v1/operacional/<int:id_mensagem>/template")
# def concluir_retorno(caso_id, retorno_id):
def atualizar_mensagem(id_mensagem):
    data = request.get_json()

    id_mensagem = data.get("id_mensagem")
    titulo = data.get("titulo")
    conteudo = data.get("conteudo")  

    try:
        conn = SessionLocal()
        if titulo:
            conn.execute(text(
            """
                UPDATE template SET titulo = :titulo WHERE id_mensagem = :id_mensagem
            """
        ),
        {
            "titulo": titulo,
            "id_mensagem": id_mensagem
        })
