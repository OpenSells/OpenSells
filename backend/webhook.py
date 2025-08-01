from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import obtener_usuario_por_email

router = APIRouter()


def actualizar_plan_usuario(db: Session, email: str, nuevo_plan: str = "pro"):
    """Actualiza el plan del usuario identificado por email."""
    usuario = obtener_usuario_por_email(email, db)
    if usuario:
        usuario.plan = nuevo_plan
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
    return usuario


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Recibe webhooks de Stripe y maneja distintos eventos."""
    payload = await request.json()
    print("Webhook recibido:", payload)

    event_type = payload.get("type")
    data_object = payload.get("data", {}).get("object", {})
    email = data_object.get("customer_email")

    if not email:
        print("Email no encontrado en payload")
        return {"status": "ok"}

    if event_type == "checkout.session.completed":
        actualizar_plan_usuario(db, email, "pro")
    elif event_type == "customer.subscription.updated":
        nickname = (
            data_object.get("items", {})
            .get("data", [{}])[0]
            .get("price", {})
            .get("nickname")
        )
        if nickname == "premium":
            actualizar_plan_usuario(db, email, "premium")
    elif event_type == "customer.subscription.deleted":
        actualizar_plan_usuario(db, email, "free")
    elif event_type == "invoice.payment_failed":
        actualizar_plan_usuario(db, email, "suspendido")
    elif event_type == "invoice.paid":
        print(f"Pago recibido para {email}")
    else:
        print(f"Evento no procesado: {event_type}")

    return {"status": "ok"}
