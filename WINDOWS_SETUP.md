# Windows 환경 설치 가이드

바이낸스 카피트레이딩 시스템을 Windows 환경에서 실행하는 방법입니다.

## 사전 요구사항

### 1. Python 3.10 이상 설치

1. [Python 공식 웹사이트](https://www.python.org/downloads/)에서 Python 3.10+ 다운로드
2. 설치 시 **"Add Python to PATH"** 체크박스 반드시 선택
3. 설치 확인:
```cmd
python --version
```

### 2. Git 설치 (선택사항)

저장소를 클론하려면 [Git for Windows](https://git-scm.com/download/win) 설치

## 설치 단계

### 1. 프로젝트 다운로드

**옵션 A: Git 사용**
```cmd
git clone https://github.com/granadu0417-crypto/copytrade.git
cd copytrade
```

**옵션 B: ZIP 다운로드**
- GitHub에서 ZIP 파일 다운로드 후 압축 해제

### 2. 가상환경 생성

```cmd
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (PowerShell)
.\venv\Scripts\Activate.ps1

# 가상환경 활성화 (CMD)
.\venv\Scripts\activate.bat
```

**참고**: PowerShell에서 실행 정책 오류가 발생하면:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. 의존성 설치

```cmd
# pip 업그레이드
python -m pip install --upgrade pip

# 필수 패키지 설치
pip install -r requirements.txt
```

### 4. Playwright 브라우저 설치

```cmd
# Playwright 브라우저 설치 (Chromium)
playwright install chromium

# 의존성 설치 (자동)
playwright install-deps chromium
```

### 5. 환경 변수 설정

1. `.env.example` 파일을 `.env`로 복사:
```cmd
copy .env.example .env
```

2. `.env` 파일을 메모장이나 에디터로 열어서 수정:
```env
# Binance API Keys
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_SECRET=your_testnet_secret_here

# Telegram Bot (선택사항)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# System Settings
MODE=testnet
DEBUG=true
```

**Binance Testnet API 키 발급 방법**:
1. https://testnet.binancefuture.com 접속
2. GitHub 계정으로 로그인
3. API 키 생성
4. `.env` 파일에 복사

### 6. 데이터베이스 초기화

```cmd
python -c "from src.database.db_manager import DatabaseManager; DatabaseManager().initialize_database()"
```

## 실행

### 방법 1: 대화형 실행

```cmd
python main.py
```

실행 모드 선택:
- `1` 입력: API 서버 모드 (웹 대시보드)
- `2` 입력: 자동 거래 모드

### 방법 2: 직접 API 서버 실행

```cmd
python -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000
```

웹 브라우저에서 접속:
```
http://localhost:8000
```

### 방법 3: 자동 거래 모드 실행

```cmd
python src/main_controller.py
```

## Windows 방화벽 설정

웹 대시보드를 외부에서 접속하려면:

1. **Windows Defender 방화벽** 열기
2. **고급 설정** → **인바운드 규칙**
3. **새 규칙** 클릭
4. **포트** 선택 → 다음
5. **TCP**, **특정 로컬 포트: 8000** 입력
6. **연결 허용** → 다음
7. 이름: "Binance Copy Trading"
8. 완료

## 백그라운드 실행 (Windows 서비스)

### 옵션 1: NSSM 사용 (추천)

1. [NSSM 다운로드](https://nssm.cc/download)
2. NSSM 설치:
```cmd
# 관리자 권한 CMD에서 실행
nssm install BinanceCopyTrading "C:\path\to\venv\Scripts\python.exe" "C:\path\to\copytrade\main.py"
```

3. 서비스 시작:
```cmd
nssm start BinanceCopyTrading
```

### 옵션 2: 작업 스케줄러

1. **작업 스케줄러** 열기
2. **기본 작업 만들기**
3. 트리거: **컴퓨터를 시작할 때**
4. 동작: **프로그램 시작**
   - 프로그램: `C:\path\to\venv\Scripts\python.exe`
   - 인수: `C:\path\to\copytrade\main.py`
5. 완료

## 트러블슈팅

### 1. Python 경로 오류

```cmd
# Python 경로 확인
where python

# PATH에 Python 추가 (시스템 환경 변수)
setx PATH "%PATH%;C:\Python310;C:\Python310\Scripts"
```

### 2. pip 설치 오류

```cmd
# pip 재설치
python -m ensurepip --upgrade
```

### 3. Playwright 설치 오류

```cmd
# PowerShell 관리자 권한으로 실행
playwright install --with-deps chromium
```

### 4. 포트 충돌 (8000번 포트 사용 중)

`config.yaml` 파일에서 포트 변경:
```yaml
webserver:
  host: "0.0.0.0"
  port: 8080  # 다른 포트로 변경
```

### 5. 한글 인코딩 오류

CMD 또는 PowerShell에서 UTF-8 설정:
```cmd
chcp 65001
```

### 6. 가상환경 활성화 안 됨

PowerShell 실행 정책 변경:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 로그 확인

로그 파일 위치:
```
C:\path\to\copytrade\logs\trading.log
C:\path\to\copytrade\logs\error.log
```

실시간 로그 확인 (PowerShell):
```powershell
Get-Content .\logs\trading.log -Wait -Tail 50
```

## 성능 최적화 (Windows)

### 1. Windows Defender 예외 추가

프로젝트 폴더를 Windows Defender 검사에서 제외:
1. **Windows 보안** → **바이러스 및 위협 방지**
2. **설정 관리** → **제외**
3. **제외 추가** → **폴더**
4. `C:\path\to\copytrade` 선택

### 2. 전원 옵션

서버 환경에서는 **고성능** 전원 옵션 선택

### 3. 자동 업데이트 비활성화

Windows 자동 재시작 방지:
- **설정** → **Windows Update** → **고급 옵션**
- **활성 시간 설정**

## 모니터링

### 작업 관리자에서 확인

1. `Ctrl + Shift + Esc` → **작업 관리자**
2. **세부 정보** 탭에서 `python.exe` 프로세스 확인
3. CPU, 메모리 사용량 모니터링

### 이벤트 뷰어

시스템 로그 확인:
```
eventvwr.msc
```

## 업데이트

```cmd
# Git Pull (Git 사용 시)
git pull origin main

# 의존성 업데이트
pip install -r requirements.txt --upgrade

# 데이터베이스 마이그레이션 (필요시)
python src/database/db_manager.py
```

## 백업

중요 파일 백업:
```cmd
# 데이터베이스 백업
copy data\trading.db backup\trading_%date%.db

# 설정 파일 백업
copy .env backup\.env.backup
copy config.yaml backup\config.yaml.backup
```

## 자동 시작 스크립트

`start.bat` 파일 생성:
```batch
@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
python main.py
pause
```

더블클릭으로 실행 가능!

## 도움말

문제가 발생하면:
1. 로그 파일 확인 (`logs/trading.log`)
2. GitHub Issues에 문의
3. Discord/Telegram 커뮤니티 문의

---

**Windows Server 2016 테스트 완료** ✅
