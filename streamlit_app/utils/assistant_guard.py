import re

BANNED_KEYWORDS = [
    "google", "google maps", "maps", "scraping", "scraper", "crawler",
    "cómo extraemos", "como extraemos", "cómo se extraen", "como se extraen",
    "páginas", "paginas", "web scraping", "scraperapi",
    "datos internos", "datos privados", "otros usuarios", "usuario ajeno",
    "contraseñas", "endpoints privados"
]

POLICY_MSG = (
    "No puedo proporcionar detalles internos de OpenSells, datos de otros usuarios ni explicar "
    "cómo se extraen leads (incluyendo referencias a Google/Google Maps o scraping). "
    "Puedo ayudarte con gestión de tus leads, tareas y textos para contactar, dentro de tu cuenta."
)

def _normalize(t: str) -> str:
    return (t or "").lower().strip()

def violates_policy(text: str):
    t = _normalize(text)
    for kw in BANNED_KEYWORDS:
        if kw in t:
            return True, POLICY_MSG
    if re.search(r"c[oó]mo?\s+.*extra(e|e?r)[a-z]*\s+leads", t):
        return True, POLICY_MSG
    if re.search(r"(dame|muestra|ens[eé]ñ(a|ame)).*(usuarios?|de otros)", t):
        return True, POLICY_MSG
    return False, ""

def sanitize_output(text: str) -> str:
    t = text
    for kw in BANNED_KEYWORDS:
        t = re.sub(re.escape(kw), "[contenido restringido]", t, flags=re.IGNORECASE)
    t = re.sub(r"(proceso|m[eé]todo|pipeline).*(leads|extracci[oó]n).*", "[contenido restringido]", t, flags=re.IGNORECASE)
    return t

__all__ = ["violates_policy", "sanitize_output", "POLICY_MSG", "BANNED_KEYWORDS"]
