@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

rem Proverka odnoy kompanii bez telegrama: oshibki vidno srazu v okne.
set PY=
python --version >nul 2>nul && set PY=python
if not defined PY ( py --version >nul 2>nul && set PY=py )
if not defined PY ( python3 --version >nul 2>nul && set PY=python3 )

if not defined PY (
  echo   Python ne nayden. Ustanovite s python.org
  pause
  exit /b 1
)

set /p INN=Vvedite INN i nazhmite Enter: 
echo.
%PY% proverka.py %INN%
echo.
pause