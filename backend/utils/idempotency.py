import hashlib
import json
from typing import List


def make_request_id(user_email_lower: str, nicho: str, geo: str, variantes_norm: List[str]) -> str:
    """Genera un hash determinista para identificar una petición de extracción."""
    payload = {
        "u": user_email_lower,
        "nicho": nicho.strip().lower(),
        "geo": geo.strip().lower(),
        "vars": variantes_norm,
        "p": 3,  # páginas fijas por variante
    }
    s = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
