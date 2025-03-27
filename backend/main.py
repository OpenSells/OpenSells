from fastapi import FastAPI, Body
from pydantic import BaseModel
from openai import OpenAI
import requests
from scraper.extractor import extraer_datos_desde_url
from fastapi.responses import FileResponse
import pandas as pd
import os
from datetime import datetime

app = FastAPI()

# ✅ Ahora usamos una variable de entorno segura
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
SCRAPERAPI_KEY = "1d904705b7ffbccf3ea2e1d5a484cb83"

class Busqueda(BaseModel):
    cliente_ideal: str

class UrlsMultiples(BaseModel):
    urls: list[str]
    pais: str = "ES"

@app.get("/")
def inicio():
    return {"mensaje": "¡Bienvenido al Wrapper Automático!"}

@app.post("/buscar")
def generar_busqueda(datos: Busqueda):
    prompt = f"Genera una búsqueda precisa en Google para encontrar {datos.cliente_ideal}, limitando a webs españolas con site:.es"
    respuesta = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    busqueda_google = respuesta.choices[0].message.content.strip().replace('"', '')

    payload = {
        'api_key': SCRAPERAPI_KEY,
        'query': busqueda_google,
        'country_code': 'es',
        'num': '10'
    }

    try:
        resultado = requests.get('https://api.scraperapi.com/structured/google/search', params=payload, timeout=60).json()
        links = [res.get('link') for res in resultado.get('organic_results', [])]

        return {
            "busqueda_generada": busqueda_google,
            "urls_obtenidas": links,
            "payload_listo": {
                "urls": links,
                "pais": "ES"
            }
        }

    except requests.exceptions.ReadTimeout:
        return {
            "error": "ScraperAPI Structured Google API tardó demasiado en responder.",
            "busqueda_generada": busqueda_google,
            "urls_obtenidas": [],
            "payload_listo": {
                "urls": [],
                "pais": "ES"
            }
        }

@app.post("/extraer_datos")
def extraer_datos_endpoint(url: str = Body(..., embed=True)):
    return extraer_datos_desde_url(url)

@app.post("/extraer_multiples")
def extraer_multiples_endpoint(payload: UrlsMultiples):
    resultados = []
    for url in payload.urls:
        try:
            datos = extraer_datos_desde_url(url, pais=payload.pais)
        except Exception as e:
            datos = {
                "url": url,
                "error": str(e)
            }
        resultados.append(datos)
    return resultados

@app.post("/exportar_csv")
def exportar_csv(payload: UrlsMultiples):
    resultados = []
    for url in payload.urls:
        try:
            datos = extraer_datos_desde_url(url, pais=payload.pais)
        except Exception as e:
            datos = {
                "url": url,
                "error": str(e)
            }
        resultados.append(datos)

    filas = []
    for item in resultados:
        if "error" in item:
            filas.append({
                "URL": item.get("url"),
                "Nombre": "ERROR",
                "Emails": "",
                "Teléfonos": "",
                "Instagram": "",
                "Facebook": "",
                "LinkedIn": "",
                "Error": item.get("error")
            })
        else:
            filas.append({
                "URL": item.get("url"),
                "Nombre": item.get("nombre_negocio"),
                "Emails": ", ".join(item.get("emails", [])),
                "Teléfonos": ", ".join(item.get("telefonos", [])),
                "Instagram": ", ".join(item.get("redes_sociales", {}).get("instagram", [])),
                "Facebook": ", ".join(item.get("redes_sociales", {}).get("facebook", [])),
                "LinkedIn": ", ".join(item.get("redes_sociales", {}).get("linkedin", [])),
                "Error": ""
            })

    df = pd.DataFrame(filas)
    df["Emails"] = df["Emails"].fillna("")
    df = df.drop_duplicates(subset=["URL", "Emails"], keep="first")
    df = df.dropna(how="all")

    export_dir = os.path.join("exports")
    os.makedirs(export_dir, exist_ok=True)

    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"leads_{now_str}.csv"
    filepath = os.path.join(export_dir, filename)

    df.to_csv(filepath, index=False, encoding='utf-8-sig')

    return FileResponse(filepath, filename=filename, media_type="text/csv")
