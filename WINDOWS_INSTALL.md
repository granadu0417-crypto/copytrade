# Windows에서 설치하기

GitHub에서 코드를 다운로드하고 실행하는 완벽 가이드입니다.

## 방법 1: Git으로 다운로드 (추천)

### 1-1. Git 설치

Git이 없다면 먼저 설치:
1. https://git-scm.com/download/win 접속
2. "64-bit Git for Windows Setup" 다운로드
3. 설치 시 모든 옵션 기본값으로 진행

### 1-2. 프로젝트 다운로드

```cmd
# 1. 원하는 폴더로 이동 (예: C:\Projects)
cd C:\Projects

# 2. Git Clone (저장소 URL을 실제 주소로 변경)
git clone https://github.com/granadu0417-crypto/copytrade.git

# 3. 프로젝트 폴더로 이동
cd copytrade

# 4. 작업 브랜치로 전환
git checkout claude/binance-copy-trading-arch-01BWz65aui4zhmXsjiT2ZCqb
```

## 방법 2: ZIP 파일로 다운로드 (간편)

### 2-1. GitHub에서 다운로드

1. GitHub 저장소 페이지 접속
2. 초록색 **"Code"** 버튼 클릭
3. **"Download ZIP"** 클릭
4. 다운로드한 ZIP 파일 압축 해제

### 2-2. 압축 해제

원하는 위치에 압축 해제 (예: `C:\Projects\copytrade`)

## 설치 및 실행

### 단계 1: Python 설치 확인

```cmd
# Python 버전 확인
python --version
```

**Python 3.10 이상**이 필요합니다.

없다면:
1. https://www.python.org/downloads/ 접속
2. Python 3.10 이상 다운로드
3. 설치 시 **"Add Python to PATH"** 체크 필수!

### 단계 2: 의존성 설치

프로젝트 폴더에서:

```cmd
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate.bat

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

### 단계 3: 환경 설정

```cmd
# .env 파일 생성
copy .env.example .env

# 메모장으로 편집
notepad .env
```

`.env` 파일에 Binance API 키 입력:

```env
# Binance API
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Testnet (테스트용)
BINANCE_TESTNET_API_KEY=your_testnet_api_key
BINANCE_TESTNET_API_SECRET=your_testnet_api_secret

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 단계 4: 실행

#### 옵션 A: GUI 런처 (가장 쉬움)

```cmd
run_gui.bat
```

더블클릭으로 실행하고 GUI에서 버튼 클릭!

#### 옵션 B: 콘솔 모드

```cmd
start.bat
```

#### 옵션 C: EXE 파일 빌드

```cmd
build_launcher.bat
```

5-10분 후 `release` 폴더에 실행 파일 생성!

## 전체 요약 (빠른 시작)

```cmd
# 1. Git Clone
git clone https://github.com/granadu0417-crypto/copytrade.git
cd copytrade
git checkout claude/binance-copy-trading-arch-01BWz65aui4zhmXsjiT2ZCqb

# 2. 가상환경 및 의존성
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
playwright install chromium

# 3. 환경 설정
copy .env.example .env
notepad .env

# 4. 실행
run_gui.bat
```

## EXE 파일로 배포하기

최종 사용자에게 Python 설치 없이 배포하려면:

```cmd
# GUI 런처 빌드
build_launcher.bat

# 또는 콘솔 버전 빌드
build_exe.bat
```

`release` 폴더를 통째로 복사하여 다른 PC에 배포!

## 업데이트 받기

나중에 코드가 업데이트되면:

```cmd
# Git으로 다운로드한 경우
git pull origin claude/binance-copy-trading-arch-01BWz65aui4zhmXsjiT2ZCqb

# ZIP으로 다운로드한 경우
# 새로 다운로드하여 덮어쓰기
```

## 폴더 구조 확인

제대로 다운로드되었는지 확인:

```
copytrade/
├── src/                    # 소스 코드
│   ├── scrapers/
│   ├── analyzers/
│   ├── executors/
│   ├── managers/
│   ├── api/
│   └── notifications/
├── frontend/               # 웹 대시보드
│   ├── index.html
│   ├── css/
│   └── js/
├── main.py                 # 메인 실행 파일
├── launcher.py             # GUI 런처
├── config.yaml             # 설정 파일
├── .env.example            # 환경 변수 예제
├── requirements.txt        # Python 의존성
├── start.bat               # 실행 스크립트
├── run_gui.bat             # GUI 실행 스크립트
├── build_exe.bat           # EXE 빌드 스크립트
└── build_launcher.bat      # GUI EXE 빌드 스크립트
```

## 자주 묻는 질문 (FAQ)

### Q: Git이 뭔가요? 필수인가요?

**A:** Git은 코드 버전 관리 도구입니다. 필수는 아니지만 업데이트 받기가 편합니다.
- **Git 사용**: `git pull` 한 번으로 업데이트
- **ZIP 사용**: 매번 새로 다운로드

### Q: Python 버전이 맞는지 확인하려면?

**A:** 명령 프롬프트에서:
```cmd
python --version
```
**Python 3.10.x** 이상이면 OK!

### Q: 가상환경을 왜 만드나요?

**A:** 프로젝트별 독립된 Python 환경을 만들기 위해서입니다.
- 다른 프로젝트와 충돌 방지
- 깔끔한 의존성 관리

### Q: Playwright 브라우저가 뭔가요?

**A:** 웹 스크래핑을 위한 자동화 브라우저입니다.
```cmd
playwright install chromium
```
약 300MB 다운로드됩니다.

### Q: Testnet API 키는 어디서 받나요?

**A:**
1. https://testnet.binancefuture.com 접속
2. GitHub 계정으로 로그인
3. API Management에서 생성

### Q: EXE 파일로 만들면 Python 없어도 되나요?

**A:** 네! 하지만:
- ✅ Python 설치 불필요
- ✅ 가상환경 불필요
- ⚠️ Playwright는 여전히 필요 (`playwright install chromium`)
- ⚠️ .env와 config.yaml은 외부 파일로 유지

### Q: 바이러스 백신에서 차단되는데요?

**A:** PyInstaller로 만든 EXE는 오탐될 수 있습니다.
- Windows Defender 예외 추가
- 또는 소스 코드로 실행 (`run_gui.bat`)

## 문제 해결

### Python을 찾을 수 없습니다

```cmd
# PATH 확인
where python
```

없으면 Python 재설치 시 **"Add Python to PATH"** 체크!

### pip가 작동하지 않습니다

```cmd
# pip 업그레이드
python -m pip install --upgrade pip
```

### 가상환경 활성화가 안 됩니다

```cmd
# PowerShell 실행 정책 변경 (관리자 권한)
Set-ExecutionPolicy RemoteSigned

# 또는 명령 프롬프트 사용 (cmd.exe)
venv\Scripts\activate.bat
```

### 포트 8000이 이미 사용 중입니다

```cmd
# config.yaml에서 포트 변경
notepad config.yaml
```

```yaml
api:
  host: "0.0.0.0"
  port: 8001  # 8000 → 8001로 변경
```

### Playwright 브라우저 다운로드 실패

```cmd
# 프록시 설정 (필요한 경우)
set HTTP_PROXY=http://your-proxy:port
set HTTPS_PROXY=http://your-proxy:port

# 재시도
playwright install chromium
```

## 다음 단계

설치 완료 후:
1. **Testnet으로 테스트** (실제 돈 없이 안전하게)
2. **웹 대시보드 확인** (http://localhost:8000)
3. **설정 조정** (config.yaml)
4. **백테스트 진행**
5. **실전 운영** (충분한 테스트 후)

---

**도움이 필요하면:**
- GitHub Issues에 질문 올리기
- config.yaml과 로그 파일 첨부
