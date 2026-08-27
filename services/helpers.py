from datetime import date, datetime, time
from zoneinfo import ZoneInfo

TZ_SP = ZoneInfo("America/Sao_Paulo")


def agora_sp() -> datetime:
    return datetime.now(TZ_SP).replace(tzinfo=None)


def texto(valor) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def vazio_para_none(valor):
    if valor is None:
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


def normalizar_campo(valor):
    if isinstance(valor, str):
        return valor.strip()
    return valor


def para_bool(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(valor)
    return str(valor).strip().lower() in ("1", "true", "sim", "s", "yes")


def calcular_idade(data_nascimento: str):
    if not data_nascimento:
        return None
    nasc = date.fromisoformat(str(data_nascimento).strip()[:10])
    hoje = agora_sp().date()
    return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))


def serializar_item(item: dict) -> dict:
    saida = {}
    for chave, valor in item.items():
        if isinstance(valor, datetime):
            saida[chave] = valor.isoformat()
        elif isinstance(valor, date):
            saida[chave] = valor.isoformat()
        elif isinstance(valor, time):
            saida[chave] = valor.isoformat()
        else:
            saida[chave] = valor
    return saida
