import requests
from bs4 import BeautifulSoup
import re
import phonenumbers

def extraer_datos_desde_url(url: str, pais: str = "ES") -> dict:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; WrapperBot/1.0)"
        }
        respuesta = requests.get(url, headers=headers, timeout=15)
        respuesta.raise_for_status()
        html = respuesta.text
        soup = BeautifulSoup(html, 'html.parser')

        # === EMAILS ===
        emails = list(set(re.findall(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            html
        )))

        # === TELÉFONOS CON VALIDACIÓN POR PAÍS ===
        raw_telefonos = re.findall(
            r"(?:\+?\d{1,3}[\s\-()]*)?(?:\d[\d\s\-()]{7,}\d)", html
        )
        telefonos = set()

        for raw in raw_telefonos:
            try:
                parsed = phonenumbers.parse(raw, pais)
                if phonenumbers.is_possible_number(parsed) and phonenumbers.is_valid_number(parsed):
                    numero_formateado = phonenumbers.format_number(
                        parsed,
                        phonenumbers.PhoneNumberFormat.INTERNATIONAL
                    )
                    telefonos.add(numero_formateado)
            except phonenumbers.NumberParseException:
                continue

        # === REDES SOCIALES ===
        redes = {
            "facebook": set(),
            "instagram": set(),
            "linkedin": set()
        }

        for link in soup.find_all("a", href=True):
            href = link['href']
            if "facebook.com" in href:
                redes["facebook"].add(href)
            elif "instagram.com" in href:
                redes["instagram"].add(href)
            elif "linkedin.com" in href:
                redes["linkedin"].add(href)

        redes = {k: list(v) for k, v in redes.items()}

        # === NOMBRE DEL NEGOCIO ===
        nombre = None
        if soup.title and soup.title.string:
            nombre = soup.title.string.strip()
        if not nombre:
            h1 = soup.find("h1")
            if h1:
                nombre = h1.get_text(strip=True)
        if not nombre:
            og_site_name = soup.find("meta", property="og:site_name")
            if og_site_name and og_site_name.get("content"):
                nombre = og_site_name["content"].strip()

        return {
            "url": url,
            "nombre_negocio": nombre,
            "emails": emails,
            "telefonos": list(telefonos),
            "redes_sociales": redes
        }

    except Exception as e:
        return {
            "url": url,
            "error": str(e)
        }
