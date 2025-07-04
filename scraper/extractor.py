import requests
from bs4 import BeautifulSoup
import re
import phonenumbers
import os
from dotenv import load_dotenv  # ✅ Carga automática de variables
from openai import OpenAI

# Cargar variables desde .env
load_dotenv()

# Inicializar cliente OpenAI con la clave cargada
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def validar_emails_por_regla(emails, dominio_base):
    preferidos = [e for e in emails if any(p in e for p in ["info", "contact", "hola", dominio_base])]
    return preferidos if preferidos else emails

def validar_telefonos_por_regla(telefonos):
    preferidos = [t for t in telefonos if not any(f in t.lower() for f in ["fax", "urgencias", "emergencia"])]
    return preferidos if preferidos else list(telefonos)

def elegir_contactos_por_ia(lista, tipo):
    if len(lista) <= 2:
        return lista

    prompt = f"""
Tengo esta lista de {tipo}s obtenidos de una página web de un negocio:

{chr(10).join(lista)}

¿Cuáles parecen más adecuados para contactar con la empresa? Puedes devolver hasta dos si tienen igual importancia. Responde solo con los {tipo}s separados por coma, sin explicar nada más.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        texto = response.choices[0].message.content.strip()
        return [x.strip() for x in texto.split(",") if x.strip()]
    except Exception as e:
        print("⚠️ Error con OpenAI:", e)
        return lista[:2]

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
        emails = list(set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html)))

        dominio_base = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        emails_filtrados = validar_emails_por_regla(emails, dominio_base)
        emails_finales = elegir_contactos_por_ia(emails_filtrados, "email") if len(emails_filtrados) > 1 else emails_filtrados

        # === TELÉFONOS ===
        raw_telefonos = re.findall(r"(?:\+?\d{1,3}[\s\-()]*)?(?:\d[\d\s\-()]{7,}\d)", html)
        telefonos = set()

        for raw in raw_telefonos:
            try:
                parsed = phonenumbers.parse(raw, pais)
                if phonenumbers.is_possible_number(parsed) and phonenumbers.is_valid_number(parsed):
                    numero_formateado = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                    telefonos.add(numero_formateado)
            except phonenumbers.NumberParseException:
                continue

        telefonos_filtrados = validar_telefonos_por_regla(telefonos)
        telefonos_finales = elegir_contactos_por_ia(telefonos_filtrados, "teléfono") if len(telefonos_filtrados) > 1 else telefonos_filtrados

        # === REDES SOCIALES ===
        redes = {"facebook": set(), "instagram": set(), "linkedin": set()}
        for link in soup.find_all("a", href=True):
            href = link['href']
            if "facebook.com" in href:
                redes["facebook"].add(href)
            elif "instagram.com" in href:
                redes["instagram"].add(href)
            elif "linkedin.com" in href:
                redes["linkedin"].add(href)
        redes = {k: list(v) for k, v in redes.items()}

        # === NOMBRE ===
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
            "emails": emails_finales,
            "telefonos": telefonos_finales,
            "redes_sociales": redes
        }

    except Exception as e:
        return {
            "url": url,
            "error": str(e)
        }
