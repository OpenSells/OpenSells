import os
import streamlit as st

HOME_PAGE = "Home.py"


def _to_page_path(target: str) -> str:
    """Normalize target to a .py path for st.switch_page."""
    if target.endswith(".py"):
        return target
    return f"{target}.py"


def go(target: str = HOME_PAGE, clear_query: bool = True):
    """Navigate safely clearing query params if desired."""
    if clear_query:
        st.query_params.clear()
    st.switch_page(_to_page_path(target))
