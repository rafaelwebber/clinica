from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from threading import Lock
import re 

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request

TOKEN_BLOCKLIST = set()

ROLE_ADMIN = 1
ROLE_OPERACIONAL = 2

_MAX_TENTATIVAS = 5
_JANELA = timedelta(minutes=15)
_LOCKOUT = timedelta(minutes=15)

_lock = Lock()
_tentativas = defaultdict(list)
_bloqueios = {}


def role_required(*roles_permitidos):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            role_id = get_jwt().get("role_id")
            if role_id not in roles_permitidos:
                return jsonify({"error": "acesso negado"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def _chave(ip: str, email: str) -> str:
    return f"{ip or 'unknown'}|{ (email or '').strip().lower() }"


def login_bloqueado(ip: str, email: str) -> tuple[bool, int]:
    key = _chave(ip, email)
    agora = datetime.utcnow()

    with _lock:
        ate = _bloqueios.get(key)
        if ate and agora < ate:
            return True, max(1, int((ate - agora).total_seconds()))
        if ate and agora >= ate:
            _bloqueios.pop(key, None)
            _tentativas.pop(key, None)
        return False, 0


def registrar_falha_login(ip: str, email: str) -> tuple[bool, int]:
    key = _chave(ip, email)
    agora = datetime.utcnow()

    with _lock:
        recentes = [
            t for t in _tentativas[key]
            if agora - t < _JANELA
        ]
        recentes.append(agora)
        _tentativas[key] = recentes

        if len(recentes) >= _MAX_TENTATIVAS:
            _bloqueios[key] = agora + _LOCKOUT
            _tentativas[key] = []
            return True, int(_LOCKOUT.total_seconds())

        return False, 0


def limpar_falhas_login(ip: str, email: str) -> None:
    key = _chave(ip, email)
    with _lock:
        _tentativas.pop(key, None)
        _bloqueios.pop(key, None)


def token_na_blocklist(jti: str) -> bool:
    return jti in TOKEN_BLOCKLIST


def revogar_token(jti: str) -> None:
    TOKEN_BLOCKLIST.add(jti)

def validar_senha(senha: str) -> bool:
    if len(senha) < 8:
        return False
    if not re.search(r'[A-Z]', senha):
        return False
    if not re.search(r'[a-z]', senha):
        return False
    if not re.search(r'[0-9]', senha):
        return False
    if not re.search(r'[^a-zA-Z0-9]', senha):
        return False
    return True #senha valida