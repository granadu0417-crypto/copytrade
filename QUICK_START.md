# 빠른 시작 가이드 ⚡

Windows에서 5분 안에 시작하기!

## 📥 다운로드

### 방법 1: Git Clone (권장)

```cmd
git clone https://github.com/granadu0417-crypto/copytrade.git
cd copytrade
git checkout claude/binance-copy-trading-arch-01BWz65aui4zhmXsjiT2ZCqb
```

### 방법 2: ZIP 다운로드

1. https://github.com/granadu0417-crypto/copytrade
2. **Code** → **Download ZIP**
3. 압축 해제

## ⚡ 자동 설치 (가장 빠름!)

```cmd
DOWNLOAD.bat
```

이 스크립트가 자동으로:
- ✅ Python 확인
- ✅ 가상환경 생성
- ✅ 모든 패키지 설치
- ✅ Playwright 브라우저 설치
- ✅ .env 파일 생성

**5분이면 완료!**

## 🔧 수동 설치

```cmd
# 1. 가상환경
python -m venv venv
venv\Scripts\activate.bat

# 2. 패키지
pip install -r requirements.txt
playwright install chromium

# 3. 설정
copy .env.example .env
notepad .env
```

## 🚀 실행

### GUI 런처 (추천!)

```cmd
run_gui.bat
```

**또는 더블클릭!**

### 콘솔 모드

```cmd
start.bat
```

## 📝 최소 설정

`.env` 파일에 필수 정보만 입력:

```env
# Testnet API (무료, 실제 돈 사용 안함)
BINANCE_TESTNET_API_KEY=발급받은_키
BINANCE_TESTNET_API_SECRET=발급받은_시크릿

# Telegram (선택사항)
TELEGRAM_BOT_TOKEN=봇토큰
TELEGRAM_CHAT_ID=채팅ID
```

### Testnet API 발급

1. https://testnet.binancefuture.com
2. GitHub 로그인
3. API Management → 생성

**무료이고 실제 돈 사용 안함!**

## 🎯 첫 실행

1. **GUI 런처 실행**: `run_gui.bat`
2. **API 서버 모드 선택** (라디오 버튼)
3. **시작 버튼 클릭**
4. **웹 브라우저**: http://localhost:8000

## 📊 웹 대시보드

```
http://localhost:8000
```

- 📈 실시간 계좌 정보
- 💰 활성 포지션
- 📊 거래 신호
- 🎯 성과 지표
- ⚙️ 시스템 제어

## 🎮 GUI 런처 사용법

```
┌─────────────────────────────────┐
│  실행 모드 선택                  │
│  ○ API 서버 (웹 대시보드)       │
│  ● 자동 거래 모드                │
├─────────────────────────────────┤
│  [▶️ 시작]  [⏹️ 중지]          │
│  [🌐 웹 대시보드 열기]          │
└─────────────────────────────────┘
```

**버튼 클릭만으로 모든 제어!**

## 🔐 보안 체크리스트

설정 전 확인:

- [ ] Testnet으로 먼저 시작 (실제 돈 사용 안함)
- [ ] .env 파일은 절대 공유 금지
- [ ] API 키는 제한적 권한만 부여
- [ ] 2단계 인증 활성화

## ⚙️ 기본 설정 (config.yaml)

추천 초기 설정:

```yaml
system:
  testnet_mode: true        # 반드시 true로 시작!
  scrape_interval: 60       # 60초마다 체크

strategy:
  min_traders_agreement: 3  # 3명 이상 합의

risk:
  max_daily_loss_percent: 5     # 하루 최대 5% 손실
  max_positions: 5              # 최대 5개 포지션
  position_size_percent: 5      # 포지션당 5%
```

## 🐛 문제 해결

### Python이 없어요

https://www.python.org/downloads/
- **Python 3.10 이상** 설치
- **"Add Python to PATH"** 체크!

### 가상환경 활성화 안돼요

```cmd
# PowerShell (관리자 권한)
Set-ExecutionPolicy RemoteSigned

# 또는 cmd.exe 사용
venv\Scripts\activate.bat
```

### 포트 8000 사용 중

`config.yaml`에서 포트 변경:

```yaml
api:
  port: 8001  # 다른 포트로 변경
```

## 📦 EXE 파일로 만들기

Python 없이 배포용:

```cmd
build_launcher.bat
```

**5-10분 후** `release/` 폴더에 EXE 생성!

## 🎓 다음 단계

1. **Testnet으로 연습** (1-2주)
2. **전략 파라미터 조정**
3. **백테스트 데이터 수집**
4. **실전 운영 (소액부터)**

## 📚 자세한 문서

- **전체 설치**: `WINDOWS_INSTALL.md`
- **EXE 빌드**: `BUILD_EXE.md`
- **Windows 설정**: `WINDOWS_SETUP.md`

## 🆘 도움말

- GitHub Issues: 버그 신고, 질문
- 로그 파일: `logs/` 폴더 확인
- 설정 파일: `config.yaml`, `.env`

---

**준비됐나요? 시작해봅시다!** 🚀

```cmd
run_gui.bat
```
