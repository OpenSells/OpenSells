@echo off
cd C:\Users\tener\proyecto-wrapper
call env\Scripts\activate.bat
uvicorn backend.main:app --reload
pause
