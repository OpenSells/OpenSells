@echo off
setlocal enabledelayedexpansion

if "%DATABASE_URL%"=="" (
  echo ERROR: DATABASE_URL no está definida
  exit /b 1
)

echo Verificando heads actuales...
alembic heads > heads.txt
set count=0
for /f %%i in (heads.txt) do (
  set /a count+=1
  set head!count!=%%i
)
if %count% GTR 1 (
  echo Hay múltiples heads: %head1% %head2%
  echo Ejecuta: alembic merge -m "merge parallel heads" %head1% %head2%
) else (
  echo Head actual: %head1%
)
del heads.txt

echo Aplicando migraciones...
alembic upgrade head

echo Heads después de migrar:
alembic heads

echo Revisa que las tablas existan en tu BD.
