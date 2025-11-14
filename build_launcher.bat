@echo off
REM GUI 런처 EXE 빌드 스크립트
echo ========================================
echo GUI 런처 EXE 빌드
echo ========================================
echo.

cd /d %~dp0

REM 가상환경 활성화
if exist "venv\Scripts\activate.bat" (
    echo [1/4] 가상환경 활성화...
    call venv\Scripts\activate.bat
)

REM PyInstaller 설치 확인
echo [2/4] PyInstaller 설치 확인...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    pip install pyinstaller
)

REM 이전 빌드 정리
echo [3/4] 이전 빌드 정리...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM GUI 런처 빌드
echo [4/4] GUI 런처 빌드 중...
pyinstaller --clean launcher.spec

REM 결과 확인
if exist "dist\BinanceCopyTrading_Launcher.exe" (
    echo.
    echo ========================================
    echo ✅ GUI 런처 빌드 완료!
    echo ========================================
    echo.
    echo 실행 파일: dist\BinanceCopyTrading_Launcher.exe
    echo.
    echo 이 런처는:
    echo   - GUI 버튼으로 시스템 시작/중지
    echo   - 설정 파일 편집 기능
    echo   - 실시간 로그 출력
    echo   - 웹 대시보드 바로가기
    echo.
) else (
    echo ❌ 빌드 실패
)

pause
