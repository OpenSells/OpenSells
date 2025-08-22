from __future__ import annotations
from datetime import datetime, date, timezone
from typing import Any, Dict, Iterable, List
import io
import pandas as pd
import unicodedata
import re


def normalize_nicho_py(s: str | None) -> str:
    s = (s or "").strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def fmt_fecha(ts: Any) -> str:
    if ts is None:
        return ""
    if isinstance(ts, datetime):
        try:
            return ts.astimezone(timezone.utc).date().isoformat()
        except Exception:
            return ts.date().isoformat()
    if isinstance(ts, date):
        return ts.isoformat()
    s = str(ts)
    return s[:10] if s else ""


def build_lead_rows(leads: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for l in leads:
        dominio = l.get("dominio") or ""
        url = l.get("url") or ""
        ts = l.get("timestamp")
        nicho = l.get("nicho") or l.get("nicho_original") or ""
        rows.append(
            {
                "Dominio": dominio or url,
                "URL": url,
                "Fecha": fmt_fecha(ts),
                "Nicho": nicho,
            }
        )
    return rows


def dataframe_from_leads(leads: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(build_lead_rows(leads))
    if df.empty:
        return pd.DataFrame(columns=["Dominio", "URL", "Fecha", "Nicho"])
    df = df.sort_values(by=["Fecha", "Dominio"], ascending=[False, True])
    df = df.drop_duplicates(subset=["Dominio", "URL"], keep="first")
    return df


def dataframe_to_csv_response(df: pd.DataFrame, filename_base: str):
    buf = io.StringIO(newline="")
    df.to_csv(buf, index=False)
    csv_text = buf.getvalue()
    csv_text_utf8_bom = "\ufeff" + csv_text
    return csv_text_utf8_bom, f"{filename_base}.csv"
