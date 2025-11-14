-- 바이낸스 카피트레이딩 시스템 데이터베이스 스키마
-- SQLite 버전

-- 트레이더 정보 테이블
CREATE TABLE IF NOT EXISTS traders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    binance_uid VARCHAR(100) UNIQUE NOT NULL,
    nickname VARCHAR(100),
    roi_7d DECIMAL(10,2),
    roi_30d DECIMAL(10,2),
    pnl DECIMAL(20,8),
    win_rate DECIMAL(5,2),
    followers INTEGER,
    total_trades INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 포지션 기록 테이블
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trader_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- LONG/SHORT
    entry_price DECIMAL(20,8) NOT NULL,
    current_price DECIMAL(20,8),
    quantity DECIMAL(20,8),
    leverage INTEGER,
    pnl DECIMAL(20,8),
    pnl_percentage DECIMAL(10,2),
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP NULL,
    is_closed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (trader_id) REFERENCES traders(id)
);

-- 거래 신호 테이블
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id VARCHAR(100) UNIQUE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    consensus_count INTEGER NOT NULL,  -- 동의한 트레이더 수
    avg_entry_price DECIMAL(20,8),
    avg_leverage DECIMAL(10,2),
    trader_ids TEXT,  -- JSON 배열로 저장
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING/EXECUTED/REJECTED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP NULL
);

-- 거래 실행 기록 테이블
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id VARCHAR(100),
    order_id VARCHAR(100),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    entry_price DECIMAL(20,8) NOT NULL,
    exit_price DECIMAL(20,8),
    quantity DECIMAL(20,8) NOT NULL,
    leverage INTEGER NOT NULL,
    pnl DECIMAL(20,8),
    pnl_percentage DECIMAL(10,2),
    commission DECIMAL(20,8),
    status VARCHAR(20) DEFAULT 'OPEN',  -- OPEN/CLOSED/CANCELLED
    close_reason VARCHAR(50),  -- TAKE_PROFIT/STOP_LOSS/MANUAL/EMERGENCY
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP NULL,
    FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
);

-- 성과 기록 테이블
CREATE TABLE IF NOT EXISTS performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2),
    total_pnl DECIMAL(20,8) DEFAULT 0,
    total_commission DECIMAL(20,8) DEFAULT 0,
    net_pnl DECIMAL(20,8) DEFAULT 0,
    max_drawdown DECIMAL(10,2),
    sharpe_ratio DECIMAL(10,4),
    total_volume DECIMAL(20,8) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 시스템 로그 테이블
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level VARCHAR(20) NOT NULL,  -- INFO/WARNING/ERROR/CRITICAL
    module VARCHAR(100),
    message TEXT NOT NULL,
    details TEXT,  -- JSON 형태의 추가 정보
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 설정 변경 이력 테이블
CREATE TABLE IF NOT EXISTS config_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(100) DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 리스크 알림 테이블
CREATE TABLE IF NOT EXISTS risk_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type VARCHAR(50) NOT NULL,  -- DAILY_LOSS/POSITION_LOSS/MAX_POSITIONS
    severity VARCHAR(20) NOT NULL,  -- WARNING/CRITICAL
    message TEXT NOT NULL,
    details TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_traders_uid ON traders(binance_uid);
CREATE INDEX IF NOT EXISTS idx_traders_active ON traders(is_active);
CREATE INDEX IF NOT EXISTS idx_positions_trader ON positions(trader_id);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_detected ON positions(detected_at);
CREATE INDEX IF NOT EXISTS idx_positions_closed ON positions(is_closed);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_trades_signal ON trades(signal_id);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_created ON trades(created_at);
CREATE INDEX IF NOT EXISTS idx_performance_date ON performance(date);
CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_created ON system_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON risk_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON risk_alerts(is_resolved);
