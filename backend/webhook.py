"""Manejo de webhooks de Stripe.

Este módulo actualiza el plan de los usuarios según los eventos recibidos de
Stripe.  Los identificadores de precio se obtienen de las variables de entorno
``STRIPE_PRICE_GRATIS``, ``STRIPE_PRICE_BASICO`` y ``STRIPE_PRICE_PREMIUM``.
"""

from __future__ import annotations

import os
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import obtener_usuario_por_email


router = APIRouter()


def actualizar_plan_usuario(db: Session, email: str, nuevo_plan: str = "free"):
    """Actualiza el plan del usuario identificado por email."""

    usuario = obtener_usuario_por_email(email, db)
    if usuario:
        usuario.plan = nuevo_plan
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
    return usuario


# Mapeo de ``price_id`` a nombre de plan
PRICE_TO_PLAN = {
    os.getenv("STRIPE_PRICE_GRATIS"): "free",
    os.getenv("STRIPE_PRICE_BASICO"): "basico",
    os.getenv("STRIPE_PRICE_PREMIUM"): "premium",
}


def _extraer_price_id(data_object: dict) -> str | None:
    """Intenta obtener el ``price_id`` desde el objeto enviado por Stripe."""

    price_id = (
        data_object.get("lines", {})
        .get("data", [{}])[0]
        .get("price", {})
        .get("id")
    )
    if not price_id:
        price_id = (
            data_object.get("items", {})
            .get("data", [{}])[0]
            .get("price", {})
            .get("id")
        )
    return price_id


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Recibe webhooks de Stripe y actualiza el plan del usuario."""

    payload = await request.json()
    print("Webhook recibido:", payload)

    event_type = payload.get("type")
    data_object = payload.get("data", {}).get("object", {})
    email = data_object.get("customer_email")

    if not email:
        print("Email no encontrado en payload")
        return {"status": "ok"}

    if event_type in {"checkout.session.completed", "customer.subscription.updated"}:
        price_id = _extraer_price_id(data_object)
        plan = PRICE_TO_PLAN.get(price_id)
        if plan:
            actualizar_plan_usuario(db, email, plan)
        else:
            print(f"price_id desconocido: {price_id}")
    elif event_type == "customer.subscription.deleted":
        actualizar_plan_usuario(db, email, "free")
    elif event_type == "invoice.payment_failed":
        actualizar_plan_usuario(db, email, "suspendido")
    elif event_type == "invoice.paid":
        print(f"Pago recibido para {email}")
    else:
        print(f"Evento no procesado: {event_type}")

    return {"status": "ok"}

