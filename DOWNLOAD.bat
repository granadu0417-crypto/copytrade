@echo off
REM 바이낸스 카피트레이딩 자동 설치 스크립트
echo ========================================
echo 바이낸스 카피트레이딩 자동 설치
echo ========================================
echo.

REM 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [경고] 관리자 권한이 없습니다.
    echo 일부 기능이 제한될 수 있습니다.
    echo.
)

REM 설치 위치 확인
set INSTALL_DIR=%CD%
echo 설치 위치: %INSTALL_DIR%
echo.

REM Python 확인
echo [1/7] Python 확인...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo.
    echo Python 3.10 이상을 설치하세요:
    echo https://www.python.org/downloads/
    echo.
    echo 설치 시 "Add Python to PATH"를 체크하세요!
    pause
    exit /b 1
) else (
    python --version
    echo ✅ Python 확인 완료
)
echo.

REM Git 확인
echo [2/7] Git 확인...
git --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Git이 설치되어 있지 않습니다.
    echo.
    echo 설치 방법을 선택하세요:
    echo   1. Git 설치 페이지 열기 (권장)
    echo   2. ZIP 파일 다운로드 안내
    echo   3. 건너뛰기
    echo.
    set /p GIT_CHOICE="선택 (1-3): "

    if "%GIT_CHOICE%"=="1" (
        start https://git-scm.com/download/win
        echo.
        echo Git 설치 후 이 스크립트를 다시 실행하세요.
        pause
        exit /b 0
    )
    if "%GIT_CHOICE%"=="2" (
        echo.
        echo GitHub에서 수동으로 다운로드:
        echo 1. https://github.com/granadu0417-crypto/copytrade 접속
        echo 2. 초록색 "Code" 버튼 클릭
        echo 3. "Download ZIP" 클릭
        echo 4. 압축 해제 후 이 스크립트 실행
        pause
        exit /b 0
    )
    echo Git 없이 계속합니다...
    set HAS_GIT=0
) else (
    git --version
    echo ✅ Git 확인 완료
    set HAS_GIT=1
)
echo.

REM 가상환경 생성
echo [3/7] 가상환경 생성...
if exist "venv" (
    echo ⚠️ 가상환경이 이미 존재합니다.
    set /p VENV_RECREATE="새로 만드시겠습니까? (y/n): "
    if /i "%VENV_RECREATE%"=="y" (
        echo 기존 가상환경 삭제 중...
        rmdir /s /q venv
        python -m venv venv
    )
) else (
    python -m venv venv
)
echo ✅ 가상환경 생성 완료
echo.

REM 가상환경 활성화
echo [4/7] 가상환경 활성화...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ 가상환경 활성화 실패
    echo.
    echo PowerShell 실행 정책 문제일 수 있습니다.
    echo 관리자 권한으로 PowerShell을 열고:
    echo   Set-ExecutionPolicy RemoteSigned
    echo.
    pause
    exit /b 1
)
echo ✅ 가상환경 활성화 완료
echo.

REM 의존성 설치
echo [5/7] Python 패키지 설치 중... (3-5분 소요)
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 패키지 설치 실패
    echo.
    echo 네트워크 연결을 확인하세요.
    pause
    exit /b 1
)
echo ✅ 패키지 설치 완료
echo.

REM Playwright 브라우저 설치
echo [6/7] Playwright 브라우저 설치 중... (약 300MB)
playwright install chromium
if errorlevel 1 (
    echo ⚠️ Playwright 설치 실패
    echo 나중에 수동으로 설치하세요: playwright install chromium
) else (
    echo ✅ Playwright 설치 완료
)
echo.

REM 환경 파일 생성
echo [7/7] 환경 설정...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo ✅ .env 파일 생성 완료
        echo.
        echo ⚠️ 중요: .env 파일에 API 키를 입력하세요!
        set /p EDIT_ENV="지금 편집하시겠습니까? (y/n): "
        if /i "%EDIT_ENV%"=="y" (
            notepad .env
        )
    ) else (
        echo ⚠️ .env.example 파일이 없습니다.
    )
) else (
    echo ✅ .env 파일이 이미 존재합니다.
)
echo.

REM 설치 완료
echo ========================================
echo ✅ 설치 완료!
echo ========================================
echo.
echo 다음 단계:
echo   1. .env 파일에 Binance API 키 입력
echo      notepad .env
echo.
echo   2. config.yaml 설정 확인
echo      notepad config.yaml
echo.
echo   3. 시스템 실행
echo      run_gui.bat      (GUI 런처)
echo      start.bat        (콘솔 모드)
echo.
echo   4. EXE 파일 빌드 (선택사항)
echo      build_launcher.bat
echo.
echo ========================================
echo.

REM 바로 실행 옵션
set /p RUN_NOW="지금 GUI 런처를 실행하시겠습니까? (y/n): "
if /i "%RUN_NOW%"=="y" (
    start run_gui.bat
)

echo.
echo 설치가 완료되었습니다. 즐거운 트레이딩 되세요! 🚀
pause
