import streamlit as st


def inject_global_css():
    st.markdown(
        """
    <style>
      :root{
        --brand:#0F172A;
        --ink:#0B1220;
        --muted:#64748B;
        --accent:#2563EB;
        --card:#FFFFFF;
        --card2:#F8FAFC;
      }
      .block-container{padding-top:1.5rem; padding-bottom:3rem;}
      .brand-title{font-size:2.1rem; font-weight:800; letter-spacing:-.02em; color:var(--brand); line-height:1}
      .brand-subtitle{margin-top:.25rem; color:var(--muted)}
      .badge{display:inline-block; padding:.4rem .7rem; border-radius:999px; font-size:.9rem; font-weight:600}
      .badge-ok{background:#E8F2FF; color:#1E40AF; border:1px solid #BFDBFE}
      .badge-warn{background:#FFF7ED; color:#9A3412; border:1px solid #FED7AA}
      .spacer-16{height:16px} .spacer-8{height:8px}

      .os-card{
        background: linear-gradient(180deg,var(--card),var(--card2));
        border:1px solid #E2E8F0;
        border-radius:16px; padding:18px;
        box-shadow: 0 1px 0 rgba(2,6,23,.04);
        transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
        height: 100%;
      }
      .os-card:hover{ transform: translateY(-2px); box-shadow: 0 12px 24px rgba(2,6,23,.06); border-color:#CBD5E1}
      .os-card .icon{font-size:22px; line-height:1}
      .os-card .title{margin-top:.35rem; font-weight:700; color:var(--ink)}
      .os-card .desc{margin:.15rem 0 .8rem 0; color:var(--muted); font-size:.95rem}
    </style>
    """,
        unsafe_allow_html=True,
    )


def action_card(
    title: str,
    desc: str,
    icon: str,
    page: str = None,
    href: str = None,
    cta: str = "Abrir",
):
    st.markdown(
        f"""
      <div class="os-card">
        <div class="icon">{icon}</div>
        <div class="title">{title}</div>
        <div class="desc">{desc}</div>
      </div>
    """,
        unsafe_allow_html=True,
    )
    if page:
        # Intentar page_link (Streamlit reciente). Fallback a switch_page.
        try:
            st.page_link(page, label=cta, icon="➡️", use_container_width=True)
        except Exception:
            try:
                from streamlit_extras.switch_page_button import (
                    switch_page,
                )  # si está instalado

                if st.button(cta, use_container_width=True):
                    switch_page(page.replace("pages/", "").replace(".py", ""))
            except Exception:
                st.write(
                    "⚠️ Ajusta el path de la página o instala switch_page. Path actual:",
                    page,
                )
    elif href:
        st.link_button(cta, href, use_container_width=True)
