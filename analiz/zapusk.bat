@echo off
chcp 65001 >nul
rem ==========================================================
rem  Запуск бота на Windows. Положите этот файл рядом с bot.py
rem  и запускайте двойным щелчком.
rem ==========================================================
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Не найден Python. Установите его с python.org,
  echo при установке отметьте галочку "Add Python to PATH".
  pause
  exit /b
)

if not exist config.ini (
  echo Нет файла config.ini. Скопируйте config.example.ini
  echo в config.ini и впишите свои ключи.
  pause
  exit /b
)

python -m pip install -q -r requirements.txt
python bot.py
pause
