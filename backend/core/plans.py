from __future__ import annotations

from typing import Optional, Dict
from pydantic import BaseModel


class PlanLimits(BaseModel):
    leads_mensuales: Optional[int]
    ia_mensajes: Optional[int]
    tareas_max: Optional[int]
    csv_exportacion: bool


PLANES: Dict[str, PlanLimits] = {
    "free": PlanLimits(
        leads_mensuales=40,
        ia_mensajes=5,
        tareas_max=4,
        csv_exportacion=False,
    ),
    "basico": PlanLimits(
        leads_mensuales=200,
        ia_mensajes=50,
        tareas_max=None,
        csv_exportacion=True,
    ),
    "premium": PlanLimits(
        leads_mensuales=600,
        ia_mensajes=None,
        tareas_max=None,
        csv_exportacion=True,
    ),
}

__all__ = ["PlanLimits", "PLANES"]
