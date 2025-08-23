import re
import unicodedata
from typing import List


def normalize_query(q: str) -> str:
    """Normaliza una cadena para comparaciones insensibles."""
    q = q.strip().lower()
    q = unicodedata.normalize("NFKD", q)
    q = "".join(c for c in q if not unicodedata.combining(c))
    q = re.sub(r"\s+", " ", q)
    return q


def dedupe_preserve_order(items: List[str]) -> List[str]:
    """Elimina duplicados preservando el orden original."""
    seen = set()
    out = []
    for it in items:
        k = normalize_query(it)
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out
