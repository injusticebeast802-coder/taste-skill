@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

rem ---- ishchem python ----
rem Skobki obyazatelny: bez nih cmd razbiraet && na verhnem urovne
rem i proverka ne srabatyvaet.
set PY=
python --version >nul 2>nul && set PY=python
if not defined PY ( py --version >nul 2>nul && set PY=py )
if not defined PY ( python3 --version >nul 2>nul && set PY=python3 )

if not defined PY (
  echo.
  echo   Python ne nayden.
  echo   Ustanovite: https://www.python.org/downloads/
  echo   Pri ustanovke otmette galochku "Add Python to PATH",
  echo   potom zapustite etot fayl snova.
  echo.
  pause
  exit /b 1
)

if not exist "config.ini" (
  echo.
  echo   Net fayla config.ini
  echo   Skopiruyte config.example.ini v config.ini
  echo   i vpishite v nego klyuchi.
  echo.
  pause
  exit /b 1
)

echo Ustanovka bibliotek...
%PY% -m pip install -q -r requirements.txt
echo.

%PY% bot.py
echo.
pause