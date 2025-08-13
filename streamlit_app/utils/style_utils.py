import streamlit as st


def full_width_button(label: str, key=None, **kwargs):
    """Render a button with consistent full-width styling.

    Parameters
    ----------
    label: str
        Text to display on the button.
    key: str, optional
        Unique key for the widget.
    **kwargs: Any
        Additional parameters forwarded to ``st.button``.
    """
    return st.button(label, key=key, use_container_width=True, **kwargs)
