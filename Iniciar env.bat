@echo off
cd /d %~dp0
if exist env\Scripts\activate.bat (
    call env\Scripts\activate.bat
    echo Entorno virtual activado.
) else (
    echo No se encontró el entorno virtual en env\Scripts\activate.bat
)
cmd
