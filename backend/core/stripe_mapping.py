from __future__ import annotations

import os

PRICE_TO_PLAN = {
    os.getenv("STRIPE_PRICE_GRATIS"): "free",
    os.getenv("STRIPE_PRICE_BASICO"): "basico",
    os.getenv("STRIPE_PRICE_PREMIUM"): "premium",
}

# Clean None keys
PRICE_TO_PLAN = {k: v for k, v in PRICE_TO_PLAN.items() if k}

__all__ = ["PRICE_TO_PLAN"]
