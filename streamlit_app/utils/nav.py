from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
HOME_PAGE = "Home.py"
LOGIN_PAGE = "pages/0_Login.py"


def _to_page_path(target: str) -> str:
    """Normalize target to a .py path for st.switch_page."""
    if target.endswith(".py"):
        page_path = target
    else:
        page_path = f"{target}.py"
    return page_path


def _exists(target: str) -> bool:
    return (BASE_DIR / target).exists()


def go(target: str = HOME_PAGE, clear_query: bool = True):
    """Navigate safely clearing query params if desired."""
    page_path = _to_page_path(target)
    if not _exists(page_path):
        st.error(f"Page not found: {page_path}")
        return
    if clear_query:
        st.query_params.clear()
    st.switch_page(page_path)
