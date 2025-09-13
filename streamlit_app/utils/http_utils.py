def parse_error_message(resp):
    """Return a human-friendly error message from a requests.Response.

    Handles JSON bodies with various shapes, lists, plain strings or even
    non-JSON responses.
    """
    try:
        data = resp.json()
    except Exception:
        return (resp.text or "").strip() or f"HTTP {getattr(resp, 'status_code', '')}".strip()

    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, dict):
            return detail.get("message") or detail.get("msg") or str(detail)
        if isinstance(detail, str):
            return detail
        return (
            data.get("message")
            or data.get("error")
            or data.get("msg")
            or str(data)
        )

    if isinstance(data, list):
        parts = []
        for item in data:
            if isinstance(item, dict):
                parts.append(item.get("msg") or str(item))
            else:
                parts.append(str(item))
        return "; ".join([p for p in parts if p]) or f"HTTP {getattr(resp, 'status_code', '')}".strip()

    return str(data) or f"HTTP {getattr(resp, 'status_code', '')}".strip()
