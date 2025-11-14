@echo off
REM 바이낸스 카피트레이딩 시스템 시작 스크립트
echo ========================================
echo 바이낸스 카피트레이딩 시스템
echo ========================================
echo.

REM 현재 디렉토리를 스크립트 위치로 변경
cd /d %~dp0

REM 가상환경 활성화 확인
if not exist "venv\Scripts\activate.bat" (
    echo [오류] 가상환경을 찾을 수 없습니다.
    echo 먼저 'python -m venv venv' 명령으로 가상환경을 생성하세요.
    pause
    exit /b 1
)

REM 가상환경 활성화
echo [1/3] 가상환경 활성화 중...
call venv\Scripts\activate.bat

REM .env 파일 존재 확인
if not exist ".env" (
    echo [경고] .env 파일이 없습니다.
    echo .env.example 파일을 복사하여 .env를 만들고 API 키를 설정하세요.
    echo.
    choice /C YN /M "계속하시겠습니까?"
    if errorlevel 2 exit /b 1
)

REM 데이터베이스 초기화 확인
if not exist "data\trading.db" (
    echo [2/3] 데이터베이스 초기화 중...
    python -c "from src.database.db_manager import DatabaseManager; DatabaseManager().initialize_database()"
    if errorlevel 1 (
        echo [오류] 데이터베이스 초기화 실패
        pause
        exit /b 1
    )
    echo 데이터베이스 초기화 완료!
) else (
    echo [2/3] 데이터베이스 확인 완료
)

REM 시스템 실행
echo [3/3] 시스템 시작 중...
echo.
python main.py

REM 오류 발생 시 대기
if errorlevel 1 (
    echo.
    echo [오류] 시스템 실행 중 오류가 발생했습니다.
    echo 로그 파일을 확인하세요: logs\trading.log
    pause
)
