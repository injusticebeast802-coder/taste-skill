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

rem ---- rabota ----
rem Bot rabotaet, poka otkryto eto okno. Esli on upal noch-yu
rem (oborvalsya internet, telegram otvetil otkazom), podnimaem ego
rem snova cherez 10 sekund. Ctrl+C i zakrytie okna bot.py schitaet
rem normalnym vyhodom i vozvrashchaet 0 - takoy zapusk ne povtoryaem.
:rabota
%PY% bot.py
rem Poryadok vazhen: "if errorlevel 2" - eto "2 i vyshe".
rem Kod 2 - ne zapolnen config.ini, perezapusk ego ne vylechit.
if errorlevel 2 goto konec
if errorlevel 1 (
  echo.
  echo Bot ostanovilsya s oshibkoy. Zapuskayu snova cherez 10 sekund.
  echo Chtoby ne perezapuskalsya - zakroyte eto okno.
  timeout /t 10 >nul
  goto rabota
)

:konec
echo.
pause
popd
