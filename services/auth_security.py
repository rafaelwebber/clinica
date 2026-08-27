from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import wraps
from threading import Lock
import hashlib
import re

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

from db import SessionLocal

TOKEN_BLOCKLIST = set()

ROLE_ADMIN = 1
ROLE_OPERACIONAL = 2

# Mensagens genéricas
MSG_CREDENCIAIS_INVALIDAS = "credenciais invalidas"
MSG_MUITAS_TENTATIVAS = "muitas tentativas. tente novamente mais tarde"
MSG_DADOS_INCOMPLETOS = "dados de login incompletos"

# Hash fixo so para equalizar tempo quando o usuario nao existe
_HASH_TIMING = generate_password_hash("timing-safe-dummy-password")

_MAX_TENTATIVAS_LOGIN = 5
_MAX_TENTATIVAS_IP = 30
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
            try:
                role_id = int(role_id)
            except (TypeError, ValueError):
                return jsonify({"error": "acesso negado"}), 403
            if role_id not in roles_permitidos:
                return jsonify({"error": "acesso negado"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def clinica_id_do_token() -> int:
    """Retorna id_clinica do JWT. Levanta ValueError se ausente/invalido."""
    clinica_id = get_jwt().get("clinica_id")
    if clinica_id is None:
        raise ValueError("clinica_id ausente no token")
    return int(clinica_id)

def _normalizar_cnpj(cnpj: str) -> str:
    return "".join(ch for ch in (cnpj or "") if ch.isdigit())


def _chave_login(ip: str, identificador: str) -> str:
    bruto = f"{ip or 'unknown'}|{(identificador or '').strip().lower()}"
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _chave_ip(ip: str) -> str:
    return f"ip|{hashlib.sha256((ip or 'unknown').encode('utf-8')).hexdigest()}"


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _estado_bloqueio(key: str) -> tuple[bool, int]:
    agora = _agora_utc()
    ate = _bloqueios.get(key)
    if ate and agora < ate:
        return True, max(1, int((ate - agora).total_seconds()))
    if ate and agora >= ate:
        _bloqueios.pop(key, None)
        _tentativas.pop(key, None)
    return False, 0


def _registrar_falha(key: str, max_tentativas: int) -> tuple[bool, int]:
    agora = _agora_utc()
    recentes = [t for t in _tentativas[key] if agora - t < _JANELA]
    recentes.append(agora)
    _tentativas[key] = recentes

    if len(recentes) >= max_tentativas:
        _bloqueios[key] = agora + _LOCKOUT
        _tentativas[key] = []
        return True, int(_LOCKOUT.total_seconds())
    return False, 0


def login_bloqueado(ip: str, identificador: str) -> tuple[bool, int]:
    with _lock:
        bloqueado_ip, seg_ip = _estado_bloqueio(_chave_ip(ip))
        if bloqueado_ip:
            return True, seg_ip
        return _estado_bloqueio(_chave_login(ip, identificador))


def registrar_falha_login(ip: str, identificador: str) -> tuple[bool, int]:
    with _lock:
        bloqueou_login, seg_login = _registrar_falha(
            _chave_login(ip, identificador),
            _MAX_TENTATIVAS_LOGIN,
        )
        bloqueou_ip, seg_ip = _registrar_falha(_chave_ip(ip), _MAX_TENTATIVAS_IP)
        if bloqueou_login or bloqueou_ip:
            return True, max(seg_login, seg_ip)
        return False, 0


def limpar_falhas_login(ip: str, identificador: str) -> None:
    with _lock:
        key = _chave_login(ip, identificador)
        _tentativas.pop(key, None)
        _bloqueios.pop(key, None)


def senha_confere(hash_armazenado: str | None, senha: str) -> bool:
    if hash_armazenado:
        return check_password_hash(hash_armazenado, senha)
    check_password_hash(_HASH_TIMING, senha)
    return False


def cnpj_valido(cnpj: str) -> bool:
    digitos = _normalizar_cnpj(cnpj)
    if len(digitos) != 14 or digitos == digitos[0] * 14:
        return False

    def _digito(base: str, pesos: list[int]) -> str:
        soma = sum(int(n) * p for n, p in zip(base, pesos))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = _digito(digitos[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = _digito(digitos[:12] + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return digitos[-2:] == d1 + d2


def normalizar_cnpj(cnpj: str) -> str:
    return _normalizar_cnpj(cnpj)


def token_na_blocklist(jti: str) -> bool:
    if jti in TOKEN_BLOCKLIST:
        return True

    conn = SessionLocal()
    try:
        row = conn.execute(
            text("SELECT jti FROM token_revogado WHERE jti = :jti"),
            {"jti": jti},
        ).first()
        if row:
            TOKEN_BLOCKLIST.add(jti)
            return True
        return False
    finally:
        conn.close()


def revogar_token(jti: str) -> None:
    TOKEN_BLOCKLIST.add(jti)
    conn = SessionLocal()
    try:
        conn.execute(
            text(
                "INSERT IGNORE INTO token_revogado (jti, criado_em) "
                "VALUES (:jti, :criado_em)"
            ),
            {"jti": jti, "criado_em": datetime.now(timezone.utc).replace(tzinfo=None)},
        )
        conn.commit()
    finally:
        conn.close()


def validar_senha(senha: str) -> bool:
    if len(senha) < 8:
        return False
    if not re.search(r"[A-Z]", senha):
        return False
    if not re.search(r"[a-z]", senha):
        return False
    if not re.search(r"[0-9]", senha):
        return False
    if not re.search(r"[^a-zA-Z0-9]", senha):
        return False
    return True
