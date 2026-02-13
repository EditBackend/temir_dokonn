@echo off
cd /d %~dp0

REM Virtualenvni ishga tushurish
call venv\Scripts\activate.bat

REM Django serverni ishga tushirish
python manage.py runserver 0.0.0.0:8000
