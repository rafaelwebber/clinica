from flask import Flask, request, Blueprint, jsonify


bp = Blueprint("admin", __name__)


@bp.get("/api/v1/admin/user")
def listar_usuario():
    id_user = request.args.get("usuario_id", type=int)
    
    if not id_user:
        return jsonify({"erro", "nao existe usuarios cadastrados"}), 404
    else:
        usuarios = request.args.get(id_user)
        return jsonify(usuarios)


@bp.post("/api/v1/admin/user")
def create_usuario():
    
    pass