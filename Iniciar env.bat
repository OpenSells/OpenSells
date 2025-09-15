@echo off
setlocal
cd /d %~dp0
if exist env\Scripts\activate.bat (
    call env\Scripts\activate.bat
    echo Entorno virtual activado.
) else (
    echo No se encontró el entorno virtual en env\Scripts\activate.bat
    pause
    exit /b 1
)
:: Fuerza el backend local para este proceso
set BACKEND_URL=http://127.0.0.1:8000
:: OJO con la mayúscula del archivo
streamlit run streamlit_app/Home.py