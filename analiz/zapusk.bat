@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

rem pushd nadezhnee chem cd /d: %~dp0 konchaetsya obratnym sleshem,
rem i "...\" inogda razbiraetsya cmd kak ekranirovannaya kavychka.
pushd "%~dp0"
echo Papka: %CD%
echo.

rem ---- ishchem python ----
rem Skobki obyazatelny: bez nih cmd razbiraet && na verhnem urovne.
set PY=
python --version >nul 2>nul && set PY=python
if not defined PY ( py --version >nul 2>nul && set PY=py )
if not defined PY ( python3 --version >nul 2>nul && set PY=python3 )

if not defined PY (
  echo   Python ne nayden.
  echo   Ustanovite: https://www.python.org/downloads/
  echo   Pri ustanovke otmette galochku "Add Python to PATH".
  echo.
  pause
  popd
  exit /b 1
)

rem ---- biblioteki ----
rem Stavim ih v oboih faylah zapuska: ran-she eto delal tolko odin,
rem i vtoroy padal s "No module named requests".
%PY% -c "import requests, PIL" >nul 2>nul
if errorlevel 1 (
  echo Ustanovka bibliotek, eto minuta...
  %PY% -m pip install --upgrade pip >nul 2>nul
  %PY% -m pip install -r requirements.txt
  echo.
  %PY% -c "import requests, PIL" >nul 2>nul
  if errorlevel 1 (
    echo   Ne udalos ustanovit biblioteki.
    echo   Proverte internet i zapustite snova.
    echo.
    pause
    popd
    exit /b 1
  )
)

%PY% bot.py
echo.
pause
popd