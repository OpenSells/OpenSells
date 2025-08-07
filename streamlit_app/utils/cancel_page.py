import streamlit as st


def show_cancel_page() -> None:
    """Display the Stripe payment cancellation page."""
    st.set_page_config(
        page_title="❌ Suscripción cancelada",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.title("❌ Suscripción cancelada")
    st.warning(
        "El proceso de pago no se ha completado. Puedes volver a intentarlo desde tu cuenta."
    )
    st.page_link("Mi Cuenta", label="👤 Volver a Mi Cuenta")
