@echo off
chcp 65001 >NUL
setlocal

REM =========================================================
REM  Script: actualizar_local.bat
REM  Objetivo: Sincronizar esta copia local con una rama remota
REM =========================================================

REM >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
REM EDITA ESTA LÍNEA ANTES DE EJECUTAR:
set "BRANCH=codex/fix-user-plan-and-data-visibility-issues"
REM Ejemplo: set "BRANCH=codex/integrate-login/register-form-in-home"
REM <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

REM Ir al directorio donde está el .bat
cd /d "%~dp0"

echo.
echo =========================================================
echo   Actualizando desde origin/%BRANCH%
echo =========================================================
echo.

REM Comprobar que git está disponible
git --version >NUL 2>&1
if errorlevel 1 (
  echo [ERROR] No se encontró Git en el PATH. Instálalo o abre este script desde "Git Bash"/"Terminal de Git".
  goto :end
)

REM Comprobar que estamos dentro de un repo git
if not exist ".git" (
  echo [ERROR] No se encontró la carpeta .git en: "%cd%"
  echo         Coloca este .bat dentro de la carpeta del repositorio o inicializa git.
  goto :end
)

REM Traer últimos cambios y cambiar a la rama
git fetch origin
git checkout "%BRANCH%"
if errorlevel 1 (
  echo [ERROR] No se pudo hacer checkout de la rama "%BRANCH%".
  goto :end
)

REM Resetear a la última versión remota
git reset --hard "origin/%BRANCH%"

echo.
echo [OK] Working copy sincronizado con origin/%BRANCH%.
echo Último commit:
git log -1 --oneline

:end
echo.
pause
endlocal
