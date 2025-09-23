import urllib.parse
import streamlit as st

# ===== Parámetros “finos” por si se quiere micro-ajustar más tarde =====
BUBBLE_SCALE = 0.86   # tamaño relativo de la burbuja respecto al viewBox (0–1)
HANDSET_SCALE = 0.98  # tamaño relativo del handset dentro de la burbuja (0–1)
# Nota: con estos valores el handset queda centrado y con buen margen sin tocar el borde.

def render_whatsapp_fab(phone_e164: str = "+34634159527", default_msg: str = "Necesito ayuda"):
    """
    Renderiza un botón flotante (FAB) de WhatsApp fijo en la esquina inferior derecha.
    """
    phone = phone_e164.lstrip("+")
    wa_url = f"https://wa.me/{phone}?text={urllib.parse.quote(default_msg)}"

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
        -webkit-font-smoothing: antialiased;
        backface-visibility: hidden;
        transform: translateZ(0);
      }
      .whatsapp-fab:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 24px rgba(0,0,0,0.28);
      }
      .whatsapp-fab svg { display:block; }
      @media (max-width:480px){
        .whatsapp-fab { width:52px; height:52px; right:14px; bottom:14px; }
      }
    </style>
    """

    # SVG profesional: burbuja con cola (stroke + relleno transparente) + handset compacto.
    # viewBox 0..256 para exactitud geométrica; se centra con translate tras aplicar scale.
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="30" height="30" role="img" aria-hidden="true">
      <!-- BURBUJA (anillo + cola) -->
      <g transform="translate(128 128)">
        <!-- Escalamos la burbuja y la re-centramos -->
        <g transform="scale({BUBBLE_SCALE}) translate(-128 -128)">
          <!-- Círculo + cola: stroke blanco, relleno transparente -->
          <path d="
            M128,28
            A100,100 0 1 1 48,62
            L42,88
            L68,80
            A100,100 0 0 0 128,28
            Z
          " fill="none" stroke="#FFFFFF" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"></path>
        </g>
      </g>

      <!-- HANDSET (teléfono) perfectamente centrado dentro de la burbuja -->
      <g transform="translate(128 128)">
        <!-- El handset vive en un cuadro de 32x32; lo escalamos y centramos -->
        <g transform="scale({BUBBLE_SCALE * HANDSET_SCALE}) translate(-16 -16)">
          <!-- Handset compacto y nítido (no toca el borde de la burbuja) -->
          <path fill="#FFFFFF" d="
            M22.8 29.6
            c-1.1-.6-6.4-3.4-7.3-3.8
            c-.9-.3-1.7-.5-2.3.4
            c-.6.9-2.7 3.6-3.2 4.2
            c-.6.7-1.2.7-2.2.3
            c-1.1-.5-4.5-1.6-8.4-4.9
            C-4 21-6.2 17.5-6.8 16.3
            c-.6-1.2 0-1.8.5-2.5
            c.5-.6 1.1-1.3 1.6-2
            c.5-.7.6-1.2 1-2
            c.3-.8.2-1.6-.1-2.3
            c-.3-.7-2.6-6.1-3.5-8.4
            C-8.1-3.5-9.1-3.1-9.9-3.1
            l-2.3 0
            c-.8 0-2.3.3-3.5 1.5
            c-1.2 1.2-4.8 4.7-4.8 11.5
            c0 6.8 5 13.3 5.7 14.3
            c.7 1 9.7 15 23.7 21
            c3.3 1.4 5.9 2.3 7.9 2.8
            c3.3 1 6.3.8 8.7.5
            c2.6-.4 8.1-3.3 9.2-6.5
            c1.2-3.2 1.1-5.9.8-6.6
            c-.3-.7-1.3-1.1-2.5-1.7
            z
          "></path>
        </g>
      </g>
    </svg>
    """

    html = f'{css}<a class="whatsapp-fab" href="{wa_url}" target="_blank" rel="noopener noreferrer" aria-label="Contactar por WhatsApp">{svg}</a>'
    st.markdown(html, unsafe_allow_html=True)
