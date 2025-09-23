import urllib.parse
import streamlit as st


def render_whatsapp_fab(
    phone_e164: str = "+34634159527",
    default_msg: str = "Necesito ayuda",
    size_px: int = 56,              # diámetro del FAB
    icon_px: int = 30,              # tamaño del SVG interno (ajustable 28–34)
    icon_scale: float = 0.92        # escala fina del glifo (0.86–0.96); da margen pro
):
    """
    Renderiza un FAB de WhatsApp (profesional) en la esquina inferior derecha.
    - Usa glifo oficial (burbuja + teléfono) en un SVG nítido.
    - 'icon_scale' ajusta el margen interno para evitar que el teléfono toque la burbuja.
    """

    phone = phone_e164.lstrip("+")
    wa_url = f"https://wa.me/{phone}?text={urllib.parse.quote(default_msg)}"

    css = f"""
    <style>
      .whatsapp-fab {{
        position: fixed;
        right: 18px;
        bottom: 18px;
        width: {size_px}px;
        height: {size_px}px;
        border-radius: 50%;
        background: #25D366;
        box-shadow: 0 8px 20px rgba(0,0,0,0.25);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        transition: transform .15s ease, box-shadow .15s ease;
        -webkit-font-smoothing: antialiased;
        backface-visibility: hidden;
        transform: translateZ(0);
      }
      .whatsapp-fab:hover {{
        transform: translateY(-1px);
        box-shadow: 0 10px 24px rgba(0,0,0,0.28);
      }
      .whatsapp-fab svg {{ display:block; }}
      @media (max-width: 480px) {{
        .whatsapp-fab {{
          width: {max(48, size_px-4)}px;
          height: {max(48, size_px-4)}px;
          right: 14px; bottom: 14px;
        }}
      }
    </style>
    """

    # Glifo oficial (vector limpio) en viewBox 0..32 (Simple Icons-like).
    # Dos paths: 1) handset  2) burbuja/anillo. Se escalan juntos y se centran.
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"
         width="{icon_px}" height="{icon_px}" role="img" aria-hidden="true">
      <g transform="translate(16,16) scale({icon_scale}) translate(-16,-16)">
        <path fill="#FFFFFF"
          d="M19.11 17.19c-.27-.14-1.6-.79-1.85-.88-.25-.09-.43-.14-.62.14-.18.27-.71.88-.86 1.06-.16.18-.32.2-.59.07-.27-.14-1.12-.41-2.13-1.3-.79-.7-1.32-1.56-1.47-1.83-.15-.27-.02-.42.11-.56.11-.11.25-.27.36-.41.12-.14.16-.23.25-.39.09-.18.05-.32-.02-.46-.07-.14-.62-1.49-.85-2.04-.22-.53-.45-.46-.62-.47l-.53-.01c-.18 0-.46.07-.7.32-.25.27-.95.93-.95 2.27 0 1.34.98 2.64 1.12 2.82.14.18 1.93 2.95 4.69 4.13.65.28 1.16.45 1.56.58.65.2 1.24.17 1.71.1.52-.08 1.6-.65 1.82-1.28.23-.63.23-1.17.16-1.28-.07-.11-.25-.18-.52-.32z"/>
        <path fill="#FFFFFF"
          d="M16.02 5.33c-5.91 0-10.69 4.78-10.69 10.69 0 1.88.49 3.64 1.35 5.16L5 27l5.99-1.57c1.49.82 3.2 1.29 5.03 1.29 5.91 0 10.69-4.78 10.69-10.69 0-5.91-4.78-10.69-10.69-10.69zm0 19.5c-1.62 0-3.13-.4-4.46-1.11l-.32-.17-3.55.93.95-3.46-.18-.33c-.83-1.35-1.31-2.93-1.31-4.65 0-4.9 3.98-8.88 8.88-8.88s8.88 3.98 8.88 8.88-3.98 8.88-8.88 8.88z"/>
      </g>
    </svg>
    """

    html = f'{css}<a class="whatsapp-fab" href="{wa_url}" target="_blank" rel="noopener noreferrer" aria-label="Contactar por WhatsApp">{svg}</a>'
    st.markdown(html, unsafe_allow_html=True)
