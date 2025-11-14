@echo off
REM 바이낸스 카피트레이딩 시스템 EXE 빌드 스크립트
echo ========================================
echo 바이낸스 카피트레이딩 EXE 빌드
echo ========================================
echo.

REM 현재 디렉토리를 스크립트 위치로 변경
cd /d %~dp0

REM 가상환경 확인 및 활성화
if exist "venv\Scripts\activate.bat" (
    echo [1/5] 가상환경 활성화...
    call venv\Scripts\activate.bat
) else (
    echo [경고] 가상환경을 찾을 수 없습니다. 시스템 Python을 사용합니다.
)

REM PyInstaller 설치 확인
echo [2/5] PyInstaller 설치 확인...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller가 설치되어 있지 않습니다. 설치 중...
    pip install pyinstaller
)

REM 이전 빌드 정리
echo [3/5] 이전 빌드 파일 정리...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM PyInstaller 실행
echo [4/5] 실행 파일 빌드 중... (5-10분 소요)
echo 이 과정은 시간이 걸릴 수 있습니다. 기다려주세요...
pyinstaller --clean copytrade.spec

REM 빌드 결과 확인
echo.
echo [5/5] 빌드 완료 확인...
if exist "dist\BinanceCopyTrading.exe" (
    echo.
    echo ========================================
    echo ✅ 빌드 성공!
    echo ========================================
    echo.
    echo 실행 파일 위치: dist\BinanceCopyTrading.exe
    echo.
    echo 다음 파일들을 함께 배포하세요:
    echo   - BinanceCopyTrading.exe
    echo   - config.yaml
    echo   - .env (API 키 설정 필요)
    echo   - frontend 폴더 (웹 대시보드)
    echo.
    echo 배포 폴더 생성 중...

    REM 배포 폴더 생성
    if not exist "release" mkdir release
    xcopy "dist\BinanceCopyTrading.exe" "release\" /Y
    xcopy "config.yaml" "release\" /Y
    xcopy ".env.example" "release\.env" /Y
    xcopy "frontend" "release\frontend\" /E /I /Y

    REM README 생성
    echo 바이낸스 카피트레이딩 시스템 > release\README.txt
    echo. >> release\README.txt
    echo 실행 방법: >> release\README.txt
    echo 1. .env 파일을 열어서 Binance API 키를 입력하세요 >> release\README.txt
    echo 2. config.yaml 파일에서 설정을 조정하세요 >> release\README.txt
    echo 3. BinanceCopyTrading.exe를 더블클릭하여 실행하세요 >> release\README.txt
    echo. >> release\README.txt
    echo 주의: Playwright 브라우저를 설치해야 합니다. >> release\README.txt
    echo playwright install chromium >> release\README.txt
    echo. >> release\README.txt

    echo.
    echo 📦 배포 패키지가 'release' 폴더에 생성되었습니다.
    echo.
    echo 다음 단계:
    echo 1. release\.env 파일에 API 키 입력
    echo 2. 명령 프롬프트에서 'playwright install chromium' 실행
    echo 3. BinanceCopyTrading.exe 실행
    echo.
) else (
    echo.
    echo ========================================
    echo ❌ 빌드 실패
    echo ========================================
    echo.
    echo 에러 로그를 확인하세요.
    echo 일반적인 문제:
    echo   - 모듈 누락: pip install -r requirements.txt
    echo   - 경로 문제: 프로젝트 루트에서 실행했는지 확인
    echo.
)

pause
