import unicodedata
import re


def normalizar_nicho(texto: str) -> str:
    """Normaliza un nombre de nicho para usarlo como clave."""
    texto = texto.strip().lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    texto = re.sub(r'[^a-z0-9]+', '_', texto)
    return texto.strip('_')
