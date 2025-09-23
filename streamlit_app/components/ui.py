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
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 32 32" fill="none" aria-hidden="true">
        <path fill="#fff" d="M19.11 17.19c-.27-.14-1.6-.79-1.85-.88-.25-.09-.43-.14-.62.14-.18.27-.71.88-.86 1.06-.16.18-.32.2-.59.07-.27-.14-1.12-.41-2.13-1.3-.79-.7-1.32-1.56-1.47-1.83-.15-.27-.02-.42.11-.56.11-.11.25-.27.36-.41.12-.14.16-.23.25-.39.09-.18.05-.32-.02-.46-.07-.14-.62-1.49-.85-2.04-.22-.53-.45-.46-.62-.47l-.53-.01c-.18 0-.46.07-.7.32-.25.27-.95.93-.95 2.27 0 1.34.98 2.64 1.12 2.82.14.18 1.93 2.95 4.69 4.13.65.28 1.16.45 1.56.58.65.2 1.24.17 1.71.1.52-.08 1.6-.65 1.82-1.28.23-.63.23-1.17.16-1.28-.07-.11-.25-.18-.52-.32z"/>
        <path fill="#fff" d="M16.02 5.33c-5.91 0-10.69 4.78-10.69 10.69 0 1.88.49 3.64 1.35 5.16L5 27l5.99-1.57c1.49.82 3.2 1.29 5.03 1.29 5.91 0 10.69-4.78 10.69-10.69 0-5.91-4.78-10.69-10.69-10.69zm0 19.5c-1.62 0-3.13-.4-4.46-1.11l-.32-.17-3.55.93.95-3.46-.18-.33c-.83-1.35-1.31-2.93-1.31-4.65 0-4.9 3.98-8.88 8.88-8.88s8.88 3.98 8.88 8.88-3.98 8.88-8.88 8.88z"/>
      </svg>
    </a>
    '''

    st.markdown(css + html, unsafe_allow_html=True)
