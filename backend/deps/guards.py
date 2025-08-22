from fastapi import Depends, HTTPException, status

from backend.auth import get_current_user
from backend.database import get_db
from backend.services.subscriptions import resolve_user_plan


def require_active_subscription(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    info = resolve_user_plan(db, current_user.email_lower)
    if info["plan_resuelto"] != "pro":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suscripción activa requerida",
        )
    return info
