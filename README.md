# 바이낸스 카피트레이딩 시스템

바이낸스 리더보드 상위 트레이더들의 거래 패턴을 분석하여 자동으로 따라 거래하는 지능형 카피트레이딩 시스템

## 주요 특징

- **다수 트레이더 종합 분석**: 15명의 상위 트레이더 동시 추적
- **동적 신호 검증**: 3명 이상 동일 방향 진입시만 거래 실행
- **2단계 검증**: 테스트넷 검증 후 실거래 전환
- **실시간 모니터링**: 웹 대시보드 및 텔레그램 알림
- **리스크 관리**: 일일 최대 손실 5%, 포지션당 10% 제한

## 시스템 구성

```
┌─────────────────────────────────────────────────────────┐
│                    사용자 인터페이스                      │
├──────────────────┬────────────────┬────────────────────┤
│   웹 대시보드    │  텔레그램 봇   │    관리자 API      │
└──────────────────┴────────────────┴────────────────────┘
                           ▲
                           │
┌─────────────────────────────────────────────────────────┐
│                    메인 컨트롤러                         │
│  - 신호 분석 엔진                                       │
│  - 거래 실행 관리                                       │
│  - 리스크 관리                                          │
└─────────────────────────────────────────────────────────┘
         ▲                 ▲                 ▲
         │                 │                 │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ 데이터 수집기  │ │  거래 실행기   │ │  모니터링      │
├────────────────┤ ├────────────────┤ ├────────────────┤
│ Web Scraper    │ │ Binance API    │ │ 성과 추적      │
│ 리더보드 추적  │ │ Testnet/Live   │ │ 로그 관리      │
└────────────────┘ └────────────────┘ └────────────────┘
```

## 설치 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. Playwright 브라우저 설치

```bash
playwright install chromium
```

### 3. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 API 키를 설정합니다:

```bash
cp .env.example .env
```

`.env` 파일 편집:
```env
BINANCE_TESTNET_API_KEY=your_testnet_api_key
BINANCE_TESTNET_SECRET=your_testnet_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 4. 데이터베이스 초기화

```bash
python -c "from src.database.db_manager import DatabaseManager; DatabaseManager().initialize_database()"
```

## 프로젝트 구조

```
copytrade/
├── src/
│   ├── scrapers/          # 웹 스크래핑 모듈
│   │   └── leaderboard_scraper.py
│   ├── analyzers/         # 신호 분석 엔진
│   │   └── signal_analyzer.py
│   ├── managers/          # 리스크 관리
│   │   └── risk_manager.py
│   ├── executors/         # 거래 실행
│   │   └── trade_executor.py
│   ├── database/          # 데이터베이스
│   │   ├── schema.sql
│   │   └── db_manager.py
│   ├── utils/             # 유틸리티
│   │   ├── logger.py
│   │   └── config_loader.py
│   ├── api/               # 웹 API
│   └── notifications/     # 텔레그램 알림
├── frontend/              # 웹 대시보드
├── tests/                 # 테스트 코드
├── data/                  # 데이터베이스
├── logs/                  # 로그 파일
├── config.yaml            # 시스템 설정
├── requirements.txt       # 의존성
└── main.py               # 메인 실행 파일
```

## 설정

`config.yaml` 파일에서 다음 항목을 설정할 수 있습니다:

### 시스템 설정
- `mode`: testnet/live (기본: testnet)
- `scraping_interval`: 리더보드 스크래핑 주기 (초)

### 거래 전략
- `tracked_traders`: 추적할 상위 트레이더 수 (기본: 15)
- `min_consensus`: 최소 동의 트레이더 수 (기본: 3)
- `time_window`: 신호 유효 시간 윈도우 (분, 기본: 5)
- `max_positions`: 최대 동시 포지션 수 (기본: 5)
- `position_size_pct`: 포지션 당 자본 비율 (기본: 0.05 = 5%)

### 리스크 관리
- `max_daily_loss`: 일일 최대 손실률 (기본: 0.05 = 5%)
- `max_position_loss`: 포지션당 최대 손실률 (기본: 0.10 = 10%)
- `stop_loss_pct`: 손절매 비율 (기본: 0.10 = 10%)
- `take_profit_pct`: 익절매 비율 (기본: 0.20 = 20%)

## 사용법

### 기본 실행

```bash
python main.py
```

### 모듈별 테스트

데이터베이스 초기화:
```bash
python src/database/db_manager.py
```

로거 테스트:
```bash
python src/utils/logger.py
```

설정 로더 테스트:
```bash
python src/utils/config_loader.py
```

## 개발 로드맵

### ✅ Phase 1: 기초 구축 (완료)
- [x] 프로젝트 디렉토리 구조 생성
- [x] requirements.txt 작성
- [x] config.yaml 설정
- [x] 데이터베이스 스키마 및 관리자
- [x] 로깅 시스템
- [x] 웹 스크래핑 모듈 (LeaderboardScraper)
- [x] 신호 분석 엔진 (SignalAnalyzer)
- [x] 리스크 관리 모듈 (RiskManager)

### 🚧 Phase 2: 핵심 기능 (진행 중)
- [ ] Binance Testnet API 연동
- [ ] 거래 실행 모듈 (TradeExecutor)
- [ ] 에러 처리 시스템

### 📋 Phase 3: 모니터링
- [ ] FastAPI 웹서버
- [ ] 웹 대시보드
- [ ] 텔레그램 봇
- [ ] 성과 분석 도구

### 🧪 Phase 4: 테스트 및 최적화
- [ ] 단위 테스트
- [ ] 통합 테스트
- [ ] Testnet 실전 테스트
- [ ] 파라미터 최적화

## 주의사항

- 본 시스템은 **교육 및 연구 목적**으로 개발되었습니다
- 실제 거래시 손실이 발생할 수 있으므로 **충분한 테스트** 후 사용하세요
- **테스트넷에서 먼저 검증**한 후 실거래로 전환하세요
- API 키는 절대 공개 저장소에 업로드하지 마세요

## 라이선스

MIT License

## 문의

프로젝트 관련 문의사항은 GitHub Issues를 통해 제출해주세요.

---

**마지막 업데이트**: 2025-01-17
**버전**: 0.1.0 (Alpha)
**상태**: 개발 중
