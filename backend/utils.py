import unicodedata
import re
from urllib.parse import urlparse


def normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def normalizar_nicho(texto: str) -> str:
    texto = texto.strip().lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    texto = re.sub(r'[^a-z0-9]+', '_', texto)
    return texto.strip('_')


def normalizar_dominio(url: str) -> str:
    if not url:
        return ""
    url = url.lower().strip()
    if url.startswith("http://") or url.startswith("https://"):
        dominio = urlparse(url).netloc
    else:
        dominio = urlparse("http://" + url).netloc
    dominio = dominio.replace("www.", "").strip()
    return dominio.split("/")[0]
