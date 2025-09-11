from __future__ import annotations

import os
from typing import Optional

# Map Stripe price IDs to internal plan names
PRICE_TO_PLAN = {
    os.getenv("STRIPE_PRICE_FREE"): "free",
    os.getenv("STRIPE_PRICE_STARTER"): "starter",
    os.getenv("STRIPE_PRICE_PRO"): "pro",
    os.getenv("STRIPE_PRICE_BUSINESS"): "business",
}

# remove None keys
PRICE_TO_PLAN = {k: v for k, v in PRICE_TO_PLAN.items() if k}


def stripe_price_to_plan(price_id: Optional[str]) -> str:
    return PRICE_TO_PLAN.get(price_id, "free")

