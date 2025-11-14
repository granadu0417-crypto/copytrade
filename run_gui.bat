@echo off
REM GUI 런처 실행 (개발 모드)
cd /d %~dp0

REM 가상환경 활성화
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM GUI 런처 실행
python launcher.py

pause
