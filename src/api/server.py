"""
FastAPI 웹서버
REST API 엔드포인트 제공
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from src.utils.logger import get_logger
from src.utils.config_loader import get_config
from src.database.db_manager import DatabaseManager
from src.executors.binance_client import BinanceClient
from src.executors.trade_executor import TradeExecutor
from src.managers.risk_manager import RiskManager
from src.analyzers.signal_analyzer import SignalAnalyzer
from src.scrapers.leaderboard_scraper import LeaderboardScraper


logger = get_logger()
config = get_config()

# FastAPI 앱 초기화
app = FastAPI(
    title="바이낸스 카피트레이딩 시스템",
    description="리더보드 상위 트레이더 자동 카피트레이딩 API",
    version="0.2.0"
)

# CORS 설정
webserver_config = config.get('webserver', default={})
cors_origins = webserver_config.get('cors_origins', ["http://localhost:8000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
try:
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
except Exception as e:
    logger.warning(f"정적 파일 디렉토리 마운트 실패: {e}")

# 전역 인스턴스
db = DatabaseManager(config.get_database_path())
binance_client = None
trade_executor = None
risk_manager = None
signal_analyzer = None
scraper = None

# 시스템 상태
system_status = {
    'is_running': False,
    'started_at': None,
    'last_scrape': None,
    'last_signal': None
}


# ===== Pydantic 모델 =====

class SignalCreate(BaseModel):
    """거래 신호 생성 요청"""
    symbol: str
    side: str
    consensus_count: int
    avg_entry_price: float
    avg_leverage: float


class TradeClose(BaseModel):
    """거래 청산 요청"""
    trade_id: int
    reason: Optional[str] = 'MANUAL'


# ===== 시스템 초기화 =====

@app.on_event("startup")
async def startup_event():
    """서버 시작시 초기화"""
    global binance_client, trade_executor, risk_manager, signal_analyzer, scraper

    logger.info("FastAPI 서버 시작 중...")

    try:
        # Binance 클라이언트 초기화
        binance_client = BinanceClient()

        # 리스크 매니저 초기화
        initial_balance = binance_client.get_balance()
        risk_manager = RiskManager(db_manager=db, initial_balance=initial_balance)

        # 거래 실행기 초기화
        trade_executor = TradeExecutor(
            binance_client=binance_client,
            risk_manager=risk_manager,
            db_manager=db
        )

        # 신호 분석기 초기화
        signal_analyzer = SignalAnalyzer(db_manager=db)

        # 스크래퍼 초기화
        scraper = LeaderboardScraper(db_manager=db)

        logger.info("모든 모듈 초기화 완료")

    except Exception as e:
        logger.error(f"초기화 실패: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료시 정리"""
    logger.info("FastAPI 서버 종료 중...")

    if scraper and scraper.browser:
        await scraper.close()


# ===== 루트 엔드포인트 =====

@app.get("/", response_class=HTMLResponse)
async def root():
    """루트 페이지 - 대시보드"""
    try:
        return FileResponse("frontend/index.html")
    except FileNotFoundError:
        return HTMLResponse(content="<h1>바이낸스 카피트레이딩 시스템</h1><p>대시보드 준비 중...</p>")


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.2.0"
    }


# ===== 시스템 상태 API =====

@app.get("/api/status")
async def get_system_status():
    """시스템 전체 상태 조회"""
    try:
        # 계정 정보
        account = binance_client.get_account_info() if binance_client else {}

        # 오픈 포지션
        open_trades = db.get_open_trades()

        # 리스크 요약
        risk_summary = risk_manager.get_risk_summary() if risk_manager else {}

        # 미해결 알림
        alerts = db.get_unresolved_alerts()

        return {
            "system": system_status,
            "account": {
                "balance": account.get('balance', 0),
                "available_balance": account.get('available_balance', 0),
                "unrealized_pnl": account.get('unrealized_pnl', 0)
            },
            "positions": {
                "open_count": len(open_trades),
                "max_positions": config.get('strategy', 'max_positions', default=5)
            },
            "risk": risk_summary,
            "alerts": {
                "total": len(alerts),
                "critical": len([a for a in alerts if a.get('severity') == 'CRITICAL'])
            }
        }
    except Exception as e:
        logger.error(f"시스템 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 포지션 관리 API =====

@app.get("/api/positions")
async def get_positions():
    """현재 오픈 포지션 조회"""
    try:
        trades = db.get_open_trades()

        # 현재 가격 및 PnL 계산
        positions_with_pnl = []
        for trade in trades:
            symbol = trade.get('symbol', '').replace('/', '')
            current_price = binance_client.get_current_price(symbol) if binance_client else None

            if current_price:
                entry_price = trade.get('entry_price', 0)
                side = trade.get('side', 'LONG')
                leverage = trade.get('leverage', 1)
                quantity = trade.get('quantity', 0)

                # PnL 계산
                if side == 'LONG':
                    pnl_pct = ((current_price - entry_price) / entry_price) * leverage * 100
                else:
                    pnl_pct = ((entry_price - current_price) / entry_price) * leverage * 100

                pnl_usdt = (quantity * entry_price) * (pnl_pct / 100) / leverage

                trade['current_price'] = current_price
                trade['pnl_pct'] = round(pnl_pct, 2)
                trade['pnl_usdt'] = round(pnl_usdt, 2)

            positions_with_pnl.append(trade)

        return {
            "count": len(positions_with_pnl),
            "positions": positions_with_pnl
        }
    except Exception as e:
        logger.error(f"포지션 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/positions/{trade_id}/close")
async def close_position(trade_id: int, data: TradeClose):
    """특정 포지션 청산"""
    try:
        if not trade_executor:
            raise HTTPException(status_code=503, detail="거래 실행기가 초기화되지 않음")

        success = trade_executor.close_trade(trade_id, reason=data.reason)

        if success:
            return {"message": f"거래 {trade_id} 청산 완료", "trade_id": trade_id}
        else:
            raise HTTPException(status_code=400, detail="거래 청산 실패")
    except Exception as e:
        logger.error(f"포지션 청산 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 트레이더 관리 API =====

@app.get("/api/traders")
async def get_traders():
    """추적 중인 트레이더 목록"""
    try:
        traders = db.get_active_traders()
        return {
            "count": len(traders),
            "traders": traders
        }
    except Exception as e:
        logger.error(f"트레이더 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 신호 관리 API =====

@app.get("/api/signals")
async def get_signals(limit: int = 20):
    """최근 거래 신호 조회"""
    try:
        # TODO: DB에서 최근 신호 조회 쿼리 추가
        return {
            "count": 0,
            "signals": []
        }
    except Exception as e:
        logger.error(f"신호 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/signals")
async def create_signal(signal: SignalCreate):
    """수동 신호 생성 (테스트용)"""
    try:
        if not trade_executor:
            raise HTTPException(status_code=503, detail="거래 실행기가 초기화되지 않음")

        signal_data = {
            'signal_id': f"manual_{datetime.now().timestamp()}",
            'symbol': signal.symbol,
            'side': signal.side,
            'consensus_count': signal.consensus_count,
            'avg_entry_price': signal.avg_entry_price,
            'avg_leverage': signal.avg_leverage
        }

        trade = trade_executor.execute_signal(signal_data)

        if trade:
            return {"message": "신호 실행 완료", "trade": trade}
        else:
            raise HTTPException(status_code=400, detail="신호 실행 실패")
    except Exception as e:
        logger.error(f"신호 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 성과 분석 API =====

@app.get("/api/performance")
async def get_performance(days: int = 30):
    """성과 데이터 조회"""
    try:
        performance = db.get_performance_history(days=days)

        # 총 통계 계산
        total_trades = sum(p.get('total_trades', 0) for p in performance)
        total_pnl = sum(p.get('total_pnl', 0) for p in performance)
        winning_trades = sum(p.get('winning_trades', 0) for p in performance)

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        return {
            "period_days": days,
            "summary": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": round(win_rate, 2),
                "total_pnl": round(total_pnl, 2)
            },
            "daily": performance
        }
    except Exception as e:
        logger.error(f"성과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 시스템 제어 API =====

@app.post("/api/control/start")
async def start_trading(background_tasks: BackgroundTasks):
    """자동 거래 시작"""
    try:
        if system_status['is_running']:
            raise HTTPException(status_code=400, detail="이미 실행 중입니다")

        system_status['is_running'] = True
        system_status['started_at'] = datetime.now().isoformat()

        # TODO: 백그라운드에서 스크래핑 및 거래 루프 시작

        logger.info("자동 거래 시작")
        return {"message": "자동 거래 시작됨", "status": system_status}
    except Exception as e:
        logger.error(f"거래 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/control/stop")
async def stop_trading():
    """자동 거래 중지"""
    try:
        if not system_status['is_running']:
            raise HTTPException(status_code=400, detail="실행 중이 아닙니다")

        system_status['is_running'] = False

        logger.info("자동 거래 중지")
        return {"message": "자동 거래 중지됨", "status": system_status}
    except Exception as e:
        logger.error(f"거래 중지 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/control/emergency")
async def emergency_stop():
    """긴급 정지 (모든 포지션 청산)"""
    try:
        if not trade_executor:
            raise HTTPException(status_code=503, detail="거래 실행기가 초기화되지 않음")

        success = trade_executor.emergency_stop()

        system_status['is_running'] = False

        if success:
            logger.critical("긴급 정지 완료")
            return {"message": "긴급 정지 완료 - 모든 포지션 청산됨"}
        else:
            raise HTTPException(status_code=500, detail="긴급 정지 실패")
    except Exception as e:
        logger.error(f"긴급 정지 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== 알림 관리 API =====

@app.get("/api/alerts")
async def get_alerts(resolved: bool = False):
    """리스크 알림 조회"""
    try:
        if resolved:
            # TODO: 해결된 알림 조회 쿼리 추가
            alerts = []
        else:
            alerts = db.get_unresolved_alerts()

        return {
            "count": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        logger.error(f"알림 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """알림 해결 처리"""
    try:
        db.resolve_alert(alert_id)
        return {"message": f"알림 {alert_id} 해결됨"}
    except Exception as e:
        logger.error(f"알림 해결 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    host = webserver_config.get('host', '0.0.0.0')
    port = webserver_config.get('port', 8000)

    logger.info(f"웹서버 시작: http://{host}:{port}")

    uvicorn.run(
        "src.api.server:app",
        host=host,
        port=port,
        reload=config.is_debug_mode()
    )
