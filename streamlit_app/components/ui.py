import urllib.parse
import streamlit as st

def render_whatsapp_fab(phone_e164: str = "+34634159527", default_msg: str = "Necesito ayuda"):
    """
    Renderiza un botón flotante de WhatsApp fijo en la esquina inferior derecha.
    - phone_e164: número en formato E.164 (con +).
    - default_msg: mensaje prellenado.
    """
    phone = phone_e164.lstrip("+")
    text = urllib.parse.quote(default_msg)
    wa_url = f"https://wa.me/{phone}?text={text}"

    # CSS en string normal (NO f-string) para evitar problemas con llaves {}
    css = """
    <style>
      .whatsapp-fab {
        position: fixed;
        right: 18px;
        bottom: 18px;
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: #25D366;
        -webkit-font-smoothing: antialiased;
        backface-visibility: hidden;
        transform: translateZ(0);
        box-shadow: 0 8px 20px rgba(0,0,0,0.25);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        transition: transform .15s ease, box-shadow .15s ease;
      }
      .whatsapp-fab:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 24px rgba(0,0,0,0.28);
      }
      @media (max-width: 480px) {
        .whatsapp-fab {
          width: 52px; height: 52px;
          right: 14px; bottom: 14px;
        }
      }
    </style>
    """

    # HTML con f-string solo para interpolar wa_url
    html = f'''
    <a class="whatsapp-fab" href="{wa_url}" target="_blank" rel="noopener noreferrer" aria-label="Contactar por WhatsApp">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="32" height="32" role="img" aria-hidden="true">
        <title>WhatsApp</title>
        <path fill="#FFFFFF" d="M128 28C73.4 28 29 72.3 29 126.9c0 17.5 4.5 34 13 48.8L28 228l53-13.9c14 7.6 29.8 11.6 47 11.6 54.6 0 98.9-44.3 98.9-98.9C226.9 72.3 182.6 28 128 28zm0 174.9c-15.8 0-30.5-4.2-43.2-11.6l-3-.1-31.4 8.3 8.4-30.3-.9-3c-7.7-12.4-12.1-26.8-12.1-42.3 0-44.9 36.4-81.3 81.3-81.3s81.3 36.4 81.3 81.3-36.4 81.3-81.3 81.3zm41.2-52.3c-2.3-1.3-13.7-7.3-15.8-8.1-2.1-.8-3.6-1.2-5.1 1.2-1.5 2.3-5.9 7.8-7.1 9.4-1.3 1.5-2.6 1.7-4.7.6-2.3-1.2-9.5-3.5-18-11.1-6.7-5.9-11.2-13.1-12.5-15.8-1.3-2.7-.1-4.1 1.1-5.6 1.2-1.4 2.6-3 3.7-4.6 1.2-1.5 1.5-2.7 2.3-4.4.8-1.8.4-3.6-.2-5.1-.6-1.5-5.7-13.6-7.8-18.6-2.2-5-4.4-4.2-6.1-4.3l-5.2-.1c-1.8 0-5.1.7-7.7 3.3-2.7 2.7-10.4 10.2-10.4 24.9 0 14.7 10.7 28.9 12.3 31.1 1.5 2.2 21.1 32.5 51.3 45.5 7.1 3.1 12.7 4.9 17.1 6.1 7.1 2.1 13.6 1.7 18.8 1 5.7-.8 17.6-7.2 20-14.1 2.5-6.9 2.5-12.8 1.8-14.2-.7-1.4-2.8-2.2-5.5-3.6z"/>
      </svg>
    </a>
    '''

    st.markdown(css + html, unsafe_allow_html=True)
