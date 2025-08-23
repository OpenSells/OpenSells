import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import get_current_user
from backend.utils.text import dedupe_preserve_order, normalize_query
from backend.utils.idempotency import make_request_id


router = APIRouter(prefix="/asistente", tags=["asistente"])


class PrepararRequest(BaseModel):
    nicho: str
    usar_nicho_existente: bool
    geo: str
    palabras_clave: Optional[str] = None


@router.post("/preparar")
async def preparar(req: PrepararRequest, usuario=Depends(get_current_user)):
    base = f"{req.nicho} {req.geo}".strip()
    variantes = [base, f"{req.nicho} cerca de {req.geo}"]
    if req.palabras_clave:
        variantes.append(f"{base} {req.palabras_clave}")
    variantes = dedupe_preserve_order(variantes)
    return {
        "nicho_preview": req.nicho.strip(),
        "geo": req.geo.strip(),
        "variantes_sugeridas": variantes,
        "mensaje": "Se extraerán como máximo 10 leads por variante. Cuantas más variantes elijas, más tardará.",
    }


class ConfirmarRequest(BaseModel):
    nicho: str
    usar_nicho_existente: bool
    geo: str
    variantes_elegidas: List[str]
    palabras_clave: Optional[str] = None


@router.post("/confirmar")
async def confirmar(req: ConfirmarRequest, usuario=Depends(get_current_user)):
    app = router.app
    variantes_dedup = dedupe_preserve_order(req.variantes_elegidas)
    variantes_norm = [normalize_query(v) for v in variantes_dedup]
    request_id = make_request_id(usuario.email_lower, req.nicho, req.geo, variantes_norm)

    if not hasattr(app.state, "asistente_jobs"):
        app.state.asistente_jobs = {}
    if not hasattr(app.state, "asistente_inflight"):
        app.state.asistente_inflight = set()

    if request_id in app.state.asistente_inflight:
        return {"status": "duplicate_ignored", "request_id": request_id}

    app.state.asistente_inflight.add(request_id)
    app.state.asistente_jobs[request_id] = {
        "fase": "preparando",
        "variante_idx": 0,
        "total_variantes": len(variantes_norm),
        "pagina_idx": 0,
        "total_paginas": 3,
        "leads_crudos": 0,
        "dominios_unicos": 0,
        "done": False,
        "error": None,
        "nicho": req.nicho,
        "geo": req.geo,
    }

    asyncio.create_task(
        _run_extraction(request_id, usuario.email_lower, req.nicho, req.geo, variantes_dedup)
    )

    return {"status": "started", "request_id": request_id}


async def _run_extraction(request_id: str, user_email_lower: str, nicho: str, geo: str, variantes: List[str]):
    app = router.app
    job = app.state.asistente_jobs[request_id]
    dominios = set()
    try:
        for idx, variante in enumerate(variantes, start=1):
            job["fase"] = f"variante {idx}/{len(variantes)}"
            job["variante_idx"] = idx
            leads_variante = 0
            for page in range(1, 4):
                job["pagina_idx"] = page
                await asyncio.sleep(0.01)
                nuevos = [f"{normalize_query(variante)}-{page}-{i}.com" for i in range(2)]
                for dominio in nuevos:
                    job["leads_crudos"] += 1
                    if dominio not in dominios:
                        dominios.add(dominio)
                        job["dominios_unicos"] = len(dominios)
                leads_variante += len(nuevos)
                if leads_variante >= 10:
                    break
        job["fase"] = "finalizado"
    except Exception as e:
        job["error"] = str(e)
    finally:
        job["done"] = True
        app.state.asistente_inflight.discard(request_id)


@router.get("/estado")
async def estado(request_id: str, usuario=Depends(get_current_user)):
    app = router.app
    job = getattr(app.state, "asistente_jobs", {}).get(request_id)
    if not job:
        raise HTTPException(status_code=404, detail="request_id not found")
    return job


@router.get("/resultados")
async def resultados(request_id: str, usuario=Depends(get_current_user)):
    app = router.app
    job = getattr(app.state, "asistente_jobs", {}).get(request_id)
    if not job:
        raise HTTPException(status_code=404, detail="request_id not found")
    if not job.get("done"):
        raise HTTPException(status_code=400, detail="job not finished")
    return {
        "nicho": job["nicho"],
        "geo": job["geo"],
        "totales": {
            "leads_crudos": job["leads_crudos"],
            "dominios_unicos": job["dominios_unicos"],
        },
    }
