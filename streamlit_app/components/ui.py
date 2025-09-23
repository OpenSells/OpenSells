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
      .whatsapp-fab svg {
        display: block;
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

        <!-- Capa 1: anillo/burbuja perfectamente centrado -->
        <!-- r=54 y stroke=14 dejan un margen cómodo dentro del botón -->
        <circle cx="128" cy="128" r="54" fill="none" stroke="#FFFFFF" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>

        <!-- Capa 2: teléfono centrado ópticamente dentro del anillo -->
        <!-- Usamos un handset compacto y lo centramos con translate al punto (128,128) -->
        <g transform="translate(128,128)">
          <!-- Scale controla el tamaño relativo del handset frente al anillo -->
          <g transform="translate(-16,-16) scale(1.15)">
            <!-- Handset estilizado (curva + cuerpo). Debe quedar claramente separado del anillo -->
            <path fill="#FFFFFF" d="M22.8 29.6c-1.1-.6-6.4-3.4-7.3-3.8-.9-.3-1.7-.5-2.3.4-.6.9-2.7 3.6-3.2 4.2-.6.7-1.2.7-2.2.3-1.1-.5-4.5-1.6-8.4-4.9C-4 21-6.2 17.5-6.8 16.3c-.6-1.2 0-1.8.5-2.5.5-.6 1.1-1.3 1.6-2 .5-.7.6-1.2 1-2 .3-.8.2-1.6-.1-2.3-.3-.7-2.6-6.1-3.5-8.4C-8.1-3.5-9.1-3.1-9.9-3.1l-2.3 0c-.8 0-2.3.3-3.5 1.5-1.2 1.2-4.8 4.7-4.8 11.5 0 6.8 5 13.3 5.7 14.3.7 1 9.7 15 23.7 21 3.3 1.4 5.9 2.3 7.9 2.8 3.3 1 6.3.8 8.7.5 2.6-.4 8.1-3.3 9.2-6.5 1.2-3.2 1.1-5.9.8-6.6-.3-.7-1.3-1.1-2.5-1.7z"/>
          </g>
        </g>
      </svg>
    </a>
    '''

    st.markdown(css + html, unsafe_allow_html=True)
