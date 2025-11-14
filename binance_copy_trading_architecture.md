# 📘 바이낸스 카피트레이딩 시스템 아키텍처 문서

## 1. 시스템 개요

### 1.1 프로젝트 목표
바이낸스 리더보드 상위 트레이더들의 거래 패턴을 분석하여 자동으로 따라 거래하는 지능형 카피트레이딩 시스템 구축

### 1.2 핵심 특징
- **다수 트레이더 종합 분석**: 단일 트레이더가 아닌 15명의 상위 트레이더 동시 추적
- **동적 신호 검증**: 3명 이상 동일 방향 진입시만 거래 실행
- **2단계 검증**: 테스트넷 검증 후 실거래 전환
- **실시간 모니터링**: 웹 대시보드 및 텔레그램 알림

## 2. 기술 스택

```yaml
운영 환경:
  서버: 카페24 Windows Server 2016 (RAM 2G, HDD 50G)
  
개발 언어:
  백엔드: Python 3.10+
  프론트엔드: HTML/CSS/JavaScript (React)
  
핵심 라이브러리:
  웹스크래핑: Playwright, BeautifulSoup4
  API 통신: python-binance, websocket-client
  웹서버: FastAPI, uvicorn
  데이터베이스: SQLite (초기) → PostgreSQL (확장시)
  스케줄링: APScheduler
  알림: python-telegram-bot
  
모니터링:
  로깅: Python logging, Loguru
  모니터링: Prometheus + Grafana (선택)
```

## 3. 시스템 구성도

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
         ▲                 ▲                 ▲
         │                 │                 │
┌─────────────────────────────────────────────────────────┐
│                      데이터베이스                        │
│  - 트레이더 정보  - 거래 내역  - 성과 지표             │
└─────────────────────────────────────────────────────────┘
```

## 4. 모듈별 상세 설계

### 4.1 데이터 수집 모듈 (Data Collector)

```python
class LeaderboardScraper:
    """
    바이낸스 리더보드 웹 스크래핑
    - 실행 주기: 60초
    - 수집 대상: 상위 15명 트레이더
    - 수집 정보: 포지션, 레버리지, 진입가, 방향
    """
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.tracked_traders = []
    
    def scrape_positions(self):
        # 1. 리더보드 페이지 접속
        # 2. 각 트레이더 상세 페이지 순회
        # 3. 현재 오픈 포지션 파싱
        # 4. 데이터베이스 저장
        pass
```

### 4.2 신호 분석 엔진 (Signal Analyzer)

```python
class SignalAnalyzer:
    """
    거래 신호 생성 로직
    """
    
    def __init__(self, config):
        self.min_consensus = config['min_consensus']  # 3명
        self.time_window = config['time_window']  # 5분
        self.tracked_traders = config['tracked_traders']  # 15명
    
    def analyze_signals(self, positions):
        """
        진입 조건 분석:
        1. 시간 윈도우 내 신규 포지션 필터링
        2. 코인별, 방향별 그룹화
        3. 동의 수 계산
        4. 조건 충족시 거래 신호 생성
        """
        signals = []
        
        # 최근 5분 내 포지션만 필터
        recent_positions = self.filter_recent(positions)
        
        # 코인-방향별 그룹화
        grouped = self.group_by_symbol_direction(recent_positions)
        
        # 진입 조건 체크
        for key, group in grouped.items():
            if len(group) >= self.min_consensus:
                signal = self.create_signal(group)
                signals.append(signal)
        
        return signals
```

### 4.3 거래 실행 모듈 (Trade Executor)

```python
class TradeExecutor:
    """
    바이낸스 API를 통한 실제 거래 실행
    """
    
    def __init__(self, api_key, api_secret, testnet=True):
        self.client = self.setup_client(api_key, api_secret, testnet)
        self.active_positions = {}
        self.max_positions = 5
    
    def execute_trade(self, signal):
        """
        거래 실행 프로세스:
        1. 리스크 체크 (포지션 수, 자금 관리)
        2. 포지션 사이즈 계산
        3. 주문 실행
        4. 손절/익절 설정
        """
        # 포지션 제한 체크
        if len(self.active_positions) >= self.max_positions:
            return False
        
        # 포지션 사이즈 계산 (자본의 5%)
        position_size = self.calculate_position_size(signal)
        
        # 레버리지 설정
        leverage = self.determine_leverage(signal)
        
        # 주문 실행
        order = self.place_order(
            symbol=signal['symbol'],
            side=signal['side'],
            quantity=position_size,
            leverage=leverage
        )
        
        return order
```

### 4.4 리스크 관리 모듈 (Risk Manager)

```python
class RiskManager:
    """
    리스크 관리 및 안전장치
    """
    
    def __init__(self):
        self.max_daily_loss = 0.05  # 5%
        self.max_position_loss = 0.10  # 10%
        self.position_size_pct = 0.05  # 5%
        
    def check_risk_limits(self):
        """
        리스크 체크 항목:
        1. 일일 최대 손실
        2. 포지션별 손실
        3. 레버리지 제한
        4. 상관관계 체크
        """
        pass
    
    def emergency_stop(self):
        """긴급 중지: 모든 포지션 청산"""
        pass
```

## 5. 데이터베이스 스키마

```sql
-- 트레이더 정보
CREATE TABLE traders (
    id INTEGER PRIMARY KEY,
    binance_uid VARCHAR(100) UNIQUE,
    nickname VARCHAR(100),
    roi_7d DECIMAL(10,2),
    roi_30d DECIMAL(10,2),
    win_rate DECIMAL(5,2),
    followers INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 포지션 기록
CREATE TABLE positions (
    id INTEGER PRIMARY KEY,
    trader_id INTEGER REFERENCES traders(id),
    symbol VARCHAR(20),
    side VARCHAR(10),  -- LONG/SHORT
    entry_price DECIMAL(20,8),
    leverage INTEGER,
    detected_at TIMESTAMP,
    closed_at TIMESTAMP NULL
);

-- 거래 실행 기록
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    signal_id VARCHAR(100),
    symbol VARCHAR(20),
    side VARCHAR(10),
    entry_price DECIMAL(20,8),
    exit_price DECIMAL(20,8),
    quantity DECIMAL(20,8),
    leverage INTEGER,
    pnl DECIMAL(20,8),
    status VARCHAR(20),  -- OPEN/CLOSED/CANCELLED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 성과 기록
CREATE TABLE performance (
    id INTEGER PRIMARY KEY,
    date DATE,
    total_trades INTEGER,
    winning_trades INTEGER,
    total_pnl DECIMAL(20,8),
    max_drawdown DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 6. 데이터 플로우

```
1. 데이터 수집 (매 60초)
   ├─> 리더보드 스크래핑
   ├─> 포지션 변화 감지
   └─> DB 저장

2. 신호 분석 (실시간)
   ├─> 시간 윈도우 필터링 (5분)
   ├─> 동의 수 계산 (최소 3명)
   └─> 거래 신호 생성

3. 거래 실행
   ├─> 리스크 체크
   ├─> 포지션 사이즈 계산
   ├─> API 주문 실행
   └─> 모니터링 시작

4. 포지션 관리
   ├─> 실시간 손익 추적
   ├─> 청산 조건 모니터링
   └─> 자동 청산 실행

5. 리포팅
   ├─> 실시간 대시보드 업데이트
   ├─> 텔레그램 알림
   └─> 일일 성과 리포트
```

## 7. 설정 파일 (config.yaml)

```yaml
# 시스템 설정
system:
  mode: "testnet"  # testnet/live
  scraping_interval: 60  # 초
  
# 거래 전략
strategy:
  tracked_traders: 15
  min_consensus: 3
  time_window: 5  # 분
  max_positions: 5
  position_size_pct: 0.05  # 5%
  
# 레버리지
leverage:
  mode: "fixed"  # fixed/average
  fixed_value: 5
  max_allowed: 10
  
# 리스크 관리
risk:
  max_daily_loss: 0.05  # 5%
  max_position_loss: 0.10  # 10%
  stop_loss_pct: 0.10  # 10%
  
# API 설정
binance:
  testnet_api_key: "YOUR_TESTNET_KEY"
  testnet_secret: "YOUR_TESTNET_SECRET"
  live_api_key: "YOUR_LIVE_KEY"
  live_secret: "YOUR_LIVE_SECRET"
  
# 알림
notifications:
  telegram:
    enabled: true
    bot_token: "YOUR_BOT_TOKEN"
    chat_id: "YOUR_CHAT_ID"
  
# 데이터베이스
database:
  type: "sqlite"
  path: "./data/trading.db"
```

## 8. 구현 로드맵

### Phase 1: 기초 구축 (1주차)
- [x] 개발 환경 설정
- [ ] 웹 스크래핑 모듈 개발
- [ ] 데이터베이스 구축
- [ ] 기본 데이터 수집 테스트

### Phase 2: 핵심 기능 (2주차)
- [ ] 신호 분석 엔진 개발
- [ ] Binance Testnet API 연동
- [ ] 거래 실행 모듈 개발
- [ ] 리스크 관리 기능 구현

### Phase 3: 모니터링 (3주차)
- [ ] 웹 대시보드 개발
- [ ] 텔레그램 봇 구현
- [ ] 실시간 모니터링 시스템
- [ ] 성과 분석 도구

### Phase 4: 테스트 및 최적화 (4주차)
- [ ] Testnet 통합 테스트
- [ ] 파라미터 최적화
- [ ] 버그 수정
- [ ] 실거래 준비

## 9. 보안 고려사항

```python
# API 키 보안
- 환경 변수 사용
- 암호화 저장
- IP 화이트리스트

# 거래 보안
- 2FA 활성화
- API 권한 최소화 (거래만 허용)
- 일일 한도 설정

# 시스템 보안
- 로그 암호화
- 정기 백업
- 접근 권한 관리
```

## 10. 모니터링 대시보드 UI

```
┌────────────────────────────────────────────────┐
│           카피트레이딩 시스템 대시보드           │
├────────────────────────────────────────────────┤
│                                                │
│  [실시간 현황]                                 │
│  • 추적 중인 트레이더: 15명                   │
│  • 활성 포지션: 3/5                           │
│  • 오늘 PnL: +5.23%                          │
│  • 현재 잔고: $10,523                        │
│                                                │
│  [최근 신호]                                   │
│  ┌──────────────────────────────────────┐    │
│  │ 12:35 | BTC/USDT | LONG | 3명 동의  │    │
│  │ 11:20 | ETH/USDT | SHORT | 실행완료 │    │
│  └──────────────────────────────────────┘    │
│                                                │
│  [포지션 현황]                                 │
│  ┌─────────┬──────┬───────┬────────┐        │
│  │ Symbol  │ Side │ PnL % │ Status │        │
│  ├─────────┼──────┼───────┼────────┤        │
│  │ BTC     │ LONG │ +2.3% │ OPEN   │        │
│  │ ETH     │ SHORT│ -0.5% │ OPEN   │        │
│  └─────────┴──────┴───────┴────────┘        │
│                                                │
│  [컨트롤]                                      │
│  [시작] [일시정지] [긴급정지] [설정]           │
└────────────────────────────────────────────────┘
```

## 11. 주요 기능별 API 엔드포인트

### 11.1 웹 API 설계

```python
# FastAPI 라우터 설계

@app.get("/api/status")
async def get_system_status():
    """시스템 상태 조회"""
    return {
        "status": "running",
        "active_positions": 3,
        "tracked_traders": 15,
        "today_pnl": 5.23
    }

@app.get("/api/positions")
async def get_positions():
    """현재 포지션 목록 조회"""
    pass

@app.post("/api/control/start")
async def start_trading():
    """자동 거래 시작"""
    pass

@app.post("/api/control/stop")
async def stop_trading():
    """자동 거래 중지"""
    pass

@app.post("/api/control/emergency")
async def emergency_stop():
    """긴급 정지 (모든 포지션 청산)"""
    pass

@app.get("/api/traders")
async def get_tracked_traders():
    """추적 중인 트레이더 목록"""
    pass

@app.post("/api/traders/add")
async def add_trader(trader_uid: str):
    """트레이더 추가"""
    pass

@app.delete("/api/traders/{trader_uid}")
async def remove_trader(trader_uid: str):
    """트레이더 제거"""
    pass

@app.get("/api/performance/daily")
async def get_daily_performance():
    """일일 성과 조회"""
    pass

@app.get("/api/logs")
async def get_system_logs():
    """시스템 로그 조회"""
    pass
```

## 12. 에러 처리 및 복구

### 12.1 예외 상황 처리

```python
class ErrorHandler:
    """
    시스템 에러 처리
    """
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 60  # 초
        
    def handle_scraping_error(self, error):
        """스크래핑 실패시"""
        # 1. 재시도
        # 2. 백업 소스 사용
        # 3. 관리자 알림
        pass
    
    def handle_api_error(self, error):
        """API 오류시"""
        # 1. Rate limit 체크
        # 2. 연결 재시도
        # 3. Fallback 모드
        pass
    
    def handle_network_error(self, error):
        """네트워크 오류시"""
        # 1. 연결 상태 확인
        # 2. 자동 재연결
        # 3. 오프라인 모드
        pass
```

### 12.2 시스템 복구 절차

```
1. 자동 복구
   - 프로세스 재시작
   - 데이터베이스 재연결
   - API 세션 갱신

2. 수동 복구
   - 관리자 알림
   - 원격 접속
   - 수동 재시작

3. 데이터 복구
   - 백업에서 복원
   - 거래 내역 동기화
   - 포지션 상태 검증
```

## 13. 성능 최적화

### 13.1 최적화 포인트

```python
# 데이터베이스 최적화
- 인덱스 설정 (trader_id, symbol, created_at)
- 쿼리 최적화
- 커넥션 풀 사용

# 스크래핑 최적화
- 병렬 처리 (asyncio)
- 캐싱 활용
- 요청 수 최소화

# 메모리 관리
- 오래된 데이터 정리
- 메모리 누수 방지
- 가비지 컬렉션 최적화
```

## 14. 테스트 계획

### 14.1 단위 테스트

```python
import pytest

def test_signal_analyzer():
    """신호 분석 테스트"""
    analyzer = SignalAnalyzer(config)
    positions = generate_test_positions()
    signals = analyzer.analyze_signals(positions)
    assert len(signals) > 0

def test_risk_manager():
    """리스크 관리 테스트"""
    risk = RiskManager()
    assert risk.check_risk_limits() == True

def test_trade_executor():
    """거래 실행 테스트"""
    executor = TradeExecutor(testnet=True)
    signal = generate_test_signal()
    order = executor.execute_trade(signal)
    assert order is not None
```

### 14.2 통합 테스트

```
1. 전체 플로우 테스트
   - 데이터 수집 → 분석 → 거래 실행
   
2. 스트레스 테스트
   - 대량 데이터 처리
   - 동시 거래 실행
   
3. 장애 테스트
   - 네트워크 장애 시뮬레이션
   - API 오류 처리
```

## 15. 운영 및 유지보수

### 15.1 일일 체크리스트

```
□ 시스템 상태 확인
□ 포지션 정합성 검증
□ 로그 파일 검토
□ 성과 지표 확인
□ 리스크 지표 모니터링
```

### 15.2 주간 작업

```
□ 성과 분석 리포트
□ 트레이더 성과 평가
□ 파라미터 조정
□ 시스템 업데이트
□ 백업 확인
```

### 15.3 월간 작업

```
□ 전체 성과 분석
□ 전략 개선
□ 시스템 최적화
□ 보안 감사
□ 비용 분석
```

## 16. 비용 분석

### 16.1 초기 투자

```
서버: 카페24 가상서버 (월 30,000원)
도메인: 선택사항 (연 15,000원)
SSL 인증서: Let's Encrypt (무료)
개발 시간: 4주
```

### 16.2 운영 비용

```
서버 유지비: 월 30,000원
거래 수수료: 거래량의 0.1%
네트워크 비용: 포함
모니터링: 무료 (오픈소스)
```

## 17. 확장 계획

### 17.1 단기 확장 (3개월)

```
- 트레이더 수 확대 (15 → 30명)
- 추가 거래소 지원 (Bybit, OKX)
- 고급 리스크 관리
- AI 기반 신호 필터링
```

### 17.2 장기 확장 (6개월)

```
- 멀티 계정 관리
- 자체 시그널 생성
- 소셜 트레이딩 플랫폼
- 모바일 앱 개발
```

## 18. 법적 고려사항

```
- 개인 투자 목적으로만 사용
- 타인 자금 운용 금지
- 거래소 이용약관 준수
- 세금 신고 의무
```

## 19. 참고 자료

### 19.1 공식 문서

- [Binance API Documentation](https://binance-docs.github.io/apidocs/)
- [Binance Testnet Guide](https://testnet.binance.vision/)
- [Python-Binance Library](https://python-binance.readthedocs.io/)

### 19.2 관련 프로젝트

- [GitHub - binance-copy-trade-bot](https://github.com/tpmmthomas/binance-copy-trade-bot)
- [Playwright Documentation](https://playwright.dev/python/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 20. 문의 및 지원

```
프로젝트 관리자: 재현
개발 환경: Windows Server 2016 / Python 3.10+
지원 채널: Telegram Bot
업데이트: GitHub Repository
```

---

**마지막 업데이트**: 2025년 1월 17일

**버전**: 1.0.0

**상태**: 개발 준비 완료
