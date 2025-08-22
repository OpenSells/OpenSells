from typing import Dict

from typing import Dict

from backend.models import Usuario


def get_tenant_email(user: Usuario) -> str:
    """Return the canonical tenant key for the current user."""
    return user.email_lower


def get_tenant_filter(user: Usuario) -> Dict[str, str]:
    """Return a filter dict scoping queries to the current tenant."""
    return {"user_email_lower": get_tenant_email(user)}
