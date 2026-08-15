from flask import Flask, jsonify, request, Blueprint
from sqlalchemy import text
from db import SessionLocal

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
            "id_cliente": id_cliente
                },)
        
        conn.commit()
        return jsonify({"mensagem":"consulta criada"}), 201
    finally:
        conn.close()