"""
데이터베이스 관리 모듈
SQLite 데이터베이스 초기화 및 CRUD 작업 관리
"""
import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class DatabaseManager:
    """데이터베이스 관리 클래스"""

    def __init__(self, db_path: str = "./data/trading.db"):
        """
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self.schema_path = Path(__file__).parent / "schema.sql"
        self._ensure_db_directory()

    def _ensure_db_directory(self):
        """데이터베이스 디렉토리 생성"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 반환"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
        return conn

    def initialize_database(self):
        """데이터베이스 초기화 (스키마 실행)"""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"스키마 파일을 찾을 수 없습니다: {self.schema_path}")

        with open(self.schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        conn = self.get_connection()
        try:
            conn.executescript(schema_sql)
            conn.commit()
            print(f"데이터베이스 초기화 완료: {self.db_path}")
        except Exception as e:
            print(f"데이터베이스 초기화 실패: {e}")
            raise
        finally:
            conn.close()

    # ===== Traders 테이블 관리 =====

    def add_trader(self, trader_data: Dict[str, Any]) -> int:
        """트레이더 추가"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO traders (binance_uid, nickname, roi_7d, roi_30d,
                                   pnl, win_rate, followers, total_trades, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(binance_uid) DO UPDATE SET
                    nickname = excluded.nickname,
                    roi_7d = excluded.roi_7d,
                    roi_30d = excluded.roi_30d,
                    pnl = excluded.pnl,
                    win_rate = excluded.win_rate,
                    followers = excluded.followers,
                    total_trades = excluded.total_trades,
                    last_updated = CURRENT_TIMESTAMP
            """, (
                trader_data.get('binance_uid'),
                trader_data.get('nickname'),
                trader_data.get('roi_7d'),
                trader_data.get('roi_30d'),
                trader_data.get('pnl'),
                trader_data.get('win_rate'),
                trader_data.get('followers'),
                trader_data.get('total_trades', 0),
                trader_data.get('is_active', True)
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_active_traders(self) -> List[Dict[str, Any]]:
        """활성화된 트레이더 목록 조회"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM traders
                WHERE is_active = TRUE
                ORDER BY roi_7d DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_trader_by_uid(self, binance_uid: str) -> Optional[Dict[str, Any]]:
        """UID로 트레이더 조회"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM traders WHERE binance_uid = ?", (binance_uid,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ===== Positions 테이블 관리 =====

    def add_position(self, position_data: Dict[str, Any]) -> int:
        """포지션 추가"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO positions (trader_id, symbol, side, entry_price,
                                     current_price, quantity, leverage, pnl, pnl_percentage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_data.get('trader_id'),
                position_data.get('symbol'),
                position_data.get('side'),
                position_data.get('entry_price'),
                position_data.get('current_price'),
                position_data.get('quantity'),
                position_data.get('leverage'),
                position_data.get('pnl'),
                position_data.get('pnl_percentage')
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_recent_positions(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """최근 N분 이내 포지션 조회"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM positions
                WHERE detected_at >= datetime('now', '-' || ? || ' minutes')
                AND is_closed = FALSE
                ORDER BY detected_at DESC
            """, (minutes,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def close_position(self, position_id: int, exit_price: float):
        """포지션 청산"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE positions
                SET is_closed = TRUE,
                    closed_at = CURRENT_TIMESTAMP,
                    current_price = ?
                WHERE id = ?
            """, (exit_price, position_id))
            conn.commit()
        finally:
            conn.close()

    # ===== Signals 테이블 관리 =====

    def add_signal(self, signal_data: Dict[str, Any]) -> int:
        """거래 신호 추가"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            trader_ids_json = json.dumps(signal_data.get('trader_ids', []))

            cursor.execute("""
                INSERT INTO signals (signal_id, symbol, side, consensus_count,
                                   avg_entry_price, avg_leverage, trader_ids, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_data.get('signal_id'),
                signal_data.get('symbol'),
                signal_data.get('side'),
                signal_data.get('consensus_count'),
                signal_data.get('avg_entry_price'),
                signal_data.get('avg_leverage'),
                trader_ids_json,
                signal_data.get('status', 'PENDING')
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_signal_status(self, signal_id: str, status: str):
        """신호 상태 업데이트"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE signals
                SET status = ?,
                    executed_at = CURRENT_TIMESTAMP
                WHERE signal_id = ?
            """, (status, signal_id))
            conn.commit()
        finally:
            conn.close()

    # ===== Trades 테이블 관리 =====

    def add_trade(self, trade_data: Dict[str, Any]) -> int:
        """거래 실행 기록 추가"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (signal_id, order_id, symbol, side, entry_price,
                                  quantity, leverage, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get('signal_id'),
                trade_data.get('order_id'),
                trade_data.get('symbol'),
                trade_data.get('side'),
                trade_data.get('entry_price'),
                trade_data.get('quantity'),
                trade_data.get('leverage'),
                trade_data.get('status', 'OPEN')
            ))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def close_trade(self, trade_id: int, exit_price: float, pnl: float,
                   close_reason: str = 'MANUAL'):
        """거래 청산"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trades
                SET status = 'CLOSED',
                    exit_price = ?,
                    pnl = ?,
                    close_reason = ?,
                    closed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (exit_price, pnl, close_reason, trade_id))
            conn.commit()
        finally:
            conn.close()

    def get_open_trades(self) -> List[Dict[str, Any]]:
        """현재 오픈된 거래 조회"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades
                WHERE status = 'OPEN'
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ===== Performance 테이블 관리 =====

    def update_daily_performance(self, date: str, performance_data: Dict[str, Any]):
        """일일 성과 업데이트"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO performance (date, total_trades, winning_trades, losing_trades,
                                       win_rate, total_pnl, total_commission, net_pnl,
                                       max_drawdown, sharpe_ratio, total_volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_trades = excluded.total_trades,
                    winning_trades = excluded.winning_trades,
                    losing_trades = excluded.losing_trades,
                    win_rate = excluded.win_rate,
                    total_pnl = excluded.total_pnl,
                    total_commission = excluded.total_commission,
                    net_pnl = excluded.net_pnl,
                    max_drawdown = excluded.max_drawdown,
                    sharpe_ratio = excluded.sharpe_ratio,
                    total_volume = excluded.total_volume
            """, (
                date,
                performance_data.get('total_trades', 0),
                performance_data.get('winning_trades', 0),
                performance_data.get('losing_trades', 0),
                performance_data.get('win_rate', 0),
                performance_data.get('total_pnl', 0),
                performance_data.get('total_commission', 0),
                performance_data.get('net_pnl', 0),
                performance_data.get('max_drawdown', 0),
                performance_data.get('sharpe_ratio', 0),
                performance_data.get('total_volume', 0)
            ))
            conn.commit()
        finally:
            conn.close()

    def get_performance_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """성과 이력 조회"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM performance
                WHERE date >= date('now', '-' || ? || ' days')
                ORDER BY date DESC
            """, (days,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ===== System Logs 테이블 관리 =====

    def add_log(self, level: str, module: str, message: str, details: Dict = None):
        """시스템 로그 추가"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            details_json = json.dumps(details) if details else None
            cursor.execute("""
                INSERT INTO system_logs (level, module, message, details)
                VALUES (?, ?, ?, ?)
            """, (level, module, message, details_json))
            conn.commit()
        finally:
            conn.close()

    # ===== Risk Alerts 테이블 관리 =====

    def add_risk_alert(self, alert_type: str, severity: str,
                      message: str, details: Dict = None):
        """리스크 알림 추가"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            details_json = json.dumps(details) if details else None
            cursor.execute("""
                INSERT INTO risk_alerts (alert_type, severity, message, details)
                VALUES (?, ?, ?, ?)
            """, (alert_type, severity, message, details_json))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_unresolved_alerts(self) -> List[Dict[str, Any]]:
        """미해결 리스크 알림 조회"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM risk_alerts
                WHERE is_resolved = FALSE
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def resolve_alert(self, alert_id: int):
        """리스크 알림 해결 처리"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE risk_alerts
                SET is_resolved = TRUE,
                    resolved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (alert_id,))
            conn.commit()
        finally:
            conn.close()


if __name__ == "__main__":
    # 테스트 코드
    db = DatabaseManager()
    db.initialize_database()
    print("데이터베이스 초기화 완료!")
