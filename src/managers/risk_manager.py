"""
리스크 관리 모듈
거래 리스크 모니터링 및 제어
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from decimal import Decimal

from src.utils.logger import get_logger
from src.utils.config_loader import get_config
from src.database.db_manager import DatabaseManager


logger = get_logger()


class RiskManager:
    """리스크 관리 클래스"""

    def __init__(self, db_manager: DatabaseManager = None, initial_balance: float = 10000.0):
        """
        Args:
            db_manager: 데이터베이스 관리자 인스턴스
            initial_balance: 초기 자본금 (USDT)
        """
        self.config = get_config()
        self.db = db_manager or DatabaseManager(self.config.get_database_path())

        # 리스크 설정 로드
        risk_config = self.config.get_risk_config()
        self.max_daily_loss = risk_config.get('max_daily_loss', 0.05)  # 5%
        self.max_position_loss = risk_config.get('max_position_loss', 0.10)  # 10%
        self.stop_loss_pct = risk_config.get('stop_loss_pct', 0.10)  # 10%
        self.take_profit_pct = risk_config.get('take_profit_pct', 0.20)  # 20%

        # 전략 설정
        strategy_config = self.config.get_strategy_config()
        self.max_positions = strategy_config.get('max_positions', 5)
        self.position_size_pct = strategy_config.get('position_size_pct', 0.05)  # 5%

        # 레버리지 설정
        leverage_config = self.config.get('leverage', default={})
        self.leverage_mode = leverage_config.get('mode', 'fixed')
        self.fixed_leverage = leverage_config.get('fixed_value', 5)
        self.max_leverage = leverage_config.get('max_allowed', 10)
        self.min_leverage = leverage_config.get('min_allowed', 1)

        # 초기 잔고
        self.initial_balance = initial_balance
        self.current_balance = initial_balance

    def check_can_open_position(self) -> tuple[bool, Optional[str]]:
        """
        새 포지션 오픈 가능 여부 확인

        Returns:
            (가능 여부, 불가 사유)
        """
        # 1. 일일 최대 손실 체크
        if not self.check_daily_loss_limit():
            return False, f"일일 최대 손실({self.max_daily_loss * 100}%) 초과"

        # 2. 최대 포지션 수 체크
        open_trades = self.db.get_open_trades()
        if len(open_trades) >= self.max_positions:
            return False, f"최대 포지션 수({self.max_positions}) 초과"

        # 3. 미해결 리스크 알림 체크
        unresolved_alerts = self.db.get_unresolved_alerts()
        critical_alerts = [
            alert for alert in unresolved_alerts
            if alert.get('severity') == 'CRITICAL'
        ]
        if critical_alerts:
            return False, f"치명적 리스크 알림 {len(critical_alerts)}건 미해결"

        return True, None

    def check_daily_loss_limit(self) -> bool:
        """일일 최대 손실 한도 체크"""
        today = date.today().isoformat()

        # 오늘 성과 조회
        performance = self.db.get_performance_history(days=1)
        if not performance:
            return True

        today_performance = performance[0] if performance else None
        if not today_performance:
            return True

        total_pnl = today_performance.get('total_pnl', 0) or 0
        net_pnl = today_performance.get('net_pnl', 0) or 0

        # 손실률 계산
        loss_pct = abs(net_pnl) / self.initial_balance if net_pnl < 0 else 0

        if loss_pct >= self.max_daily_loss:
            logger.warning(
                f"일일 최대 손실 한도 도달: {loss_pct * 100:.2f}% "
                f"(한도: {self.max_daily_loss * 100}%)"
            )
            self._create_risk_alert(
                'DAILY_LOSS',
                'CRITICAL',
                f"일일 손실 {loss_pct * 100:.2f}% 도달",
                {'loss_pct': loss_pct, 'loss_amount': net_pnl}
            )
            return False

        return True

    def calculate_position_size(
        self,
        signal: Dict[str, Any],
        current_balance: float = None
    ) -> float:
        """
        포지션 사이즈 계산

        Args:
            signal: 거래 신호
            current_balance: 현재 잔고 (None이면 초기 잔고 사용)

        Returns:
            포지션 사이즈 (USDT)
        """
        balance = current_balance if current_balance is not None else self.current_balance

        # 자본의 일정 비율로 포지션 사이즈 결정
        position_size = balance * self.position_size_pct

        logger.info(
            f"포지션 사이즈 계산: {position_size:.2f} USDT "
            f"(잔고: {balance:.2f}, 비율: {self.position_size_pct * 100}%)"
        )

        return position_size

    def determine_leverage(self, signal: Dict[str, Any]) -> int:
        """
        레버리지 결정

        Args:
            signal: 거래 신호

        Returns:
            레버리지 값
        """
        if self.leverage_mode == 'fixed':
            leverage = self.fixed_leverage

        elif self.leverage_mode == 'average':
            # 신호의 평균 레버리지 사용
            avg_leverage = signal.get('avg_leverage', self.fixed_leverage)
            leverage = int(avg_leverage)

        elif self.leverage_mode == 'adaptive':
            # 신호 강도에 따라 동적 조정
            consensus_count = signal.get('consensus_count', 0)
            min_consensus = self.config.get('strategy', 'min_consensus', default=3)

            # 컨센서스가 높을수록 높은 레버리지
            ratio = min(consensus_count / (min_consensus * 2), 1.0)
            leverage = int(self.min_leverage + (self.max_leverage - self.min_leverage) * ratio)

        else:
            leverage = self.fixed_leverage

        # 레버리지 제한 적용
        leverage = max(self.min_leverage, min(leverage, self.max_leverage))

        logger.info(f"레버리지 결정: {leverage}x (모드: {self.leverage_mode})")
        return leverage

    def calculate_stop_loss_price(
        self,
        entry_price: float,
        side: str
    ) -> float:
        """
        손절가 계산

        Args:
            entry_price: 진입가
            side: 포지션 방향 (LONG/SHORT)

        Returns:
            손절가
        """
        if side.upper() == 'LONG':
            stop_loss = entry_price * (1 - self.stop_loss_pct)
        else:  # SHORT
            stop_loss = entry_price * (1 + self.stop_loss_pct)

        logger.debug(
            f"손절가 계산: {stop_loss:.2f} "
            f"(진입가: {entry_price:.2f}, 방향: {side}, 비율: {self.stop_loss_pct * 100}%)"
        )

        return stop_loss

    def calculate_take_profit_price(
        self,
        entry_price: float,
        side: str
    ) -> float:
        """
        익절가 계산

        Args:
            entry_price: 진입가
            side: 포지션 방향 (LONG/SHORT)

        Returns:
            익절가
        """
        if side.upper() == 'LONG':
            take_profit = entry_price * (1 + self.take_profit_pct)
        else:  # SHORT
            take_profit = entry_price * (1 - self.take_profit_pct)

        logger.debug(
            f"익절가 계산: {take_profit:.2f} "
            f"(진입가: {entry_price:.2f}, 방향: {side}, 비율: {self.take_profit_pct * 100}%)"
        )

        return take_profit

    def check_position_risk(
        self,
        trade: Dict[str, Any],
        current_price: float
    ) -> Dict[str, Any]:
        """
        개별 포지션 리스크 체크

        Args:
            trade: 거래 정보
            current_price: 현재 가격

        Returns:
            리스크 체크 결과
        """
        entry_price = trade.get('entry_price', 0)
        side = trade.get('side', 'LONG').upper()
        quantity = trade.get('quantity', 0)
        leverage = trade.get('leverage', 1)

        # PnL 계산
        if side == 'LONG':
            pnl_pct = ((current_price - entry_price) / entry_price) * leverage
        else:  # SHORT
            pnl_pct = ((entry_price - current_price) / entry_price) * leverage

        # 손절/익절 가격
        stop_loss = self.calculate_stop_loss_price(entry_price, side)
        take_profit = self.calculate_take_profit_price(entry_price, side)

        # 손절/익절 트리거 체크
        should_stop_loss = False
        should_take_profit = False

        if side == 'LONG':
            should_stop_loss = current_price <= stop_loss
            should_take_profit = current_price >= take_profit
        else:  # SHORT
            should_stop_loss = current_price >= stop_loss
            should_take_profit = current_price <= take_profit

        result = {
            'trade_id': trade.get('id'),
            'symbol': trade.get('symbol'),
            'side': side,
            'entry_price': entry_price,
            'current_price': current_price,
            'pnl_pct': pnl_pct * 100,  # 퍼센티지
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'should_stop_loss': should_stop_loss,
            'should_take_profit': should_take_profit,
            'action_required': should_stop_loss or should_take_profit
        }

        # 위험 상황 알림
        if should_stop_loss:
            logger.warning(
                f"손절 트리거: {trade.get('symbol')} {side} | "
                f"손실: {pnl_pct * 100:.2f}%"
            )
            self._create_risk_alert(
                'POSITION_LOSS',
                'CRITICAL',
                f"손절 트리거: {trade.get('symbol')} {side}",
                result
            )

        elif pnl_pct < -self.max_position_loss:
            logger.error(
                f"최대 포지션 손실 초과: {trade.get('symbol')} {side} | "
                f"손실: {pnl_pct * 100:.2f}%"
            )
            self._create_risk_alert(
                'POSITION_LOSS',
                'CRITICAL',
                f"최대 손실 초과: {trade.get('symbol')} {side}",
                result
            )

        return result

    def emergency_stop(self) -> bool:
        """
        긴급 정지 (모든 포지션 청산)

        Returns:
            성공 여부
        """
        logger.critical("긴급 정지 실행: 모든 포지션 청산")

        try:
            open_trades = self.db.get_open_trades()

            for trade in open_trades:
                # 청산 처리 (실제 거래소 API 호출은 TradeExecutor에서 처리)
                logger.warning(
                    f"긴급 청산: {trade.get('symbol')} {trade.get('side')} "
                    f"(Trade ID: {trade.get('id')})"
                )

            self._create_risk_alert(
                'EMERGENCY_STOP',
                'CRITICAL',
                f"긴급 정지 실행: {len(open_trades)}개 포지션 청산",
                {'trade_count': len(open_trades)}
            )

            return True

        except Exception as e:
            logger.error(f"긴급 정지 실패: {e}")
            return False

    def _create_risk_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        details: Dict = None
    ):
        """리스크 알림 생성"""
        try:
            self.db.add_risk_alert(alert_type, severity, message, details)
            logger.info(f"리스크 알림 생성: [{severity}] {message}")
        except Exception as e:
            logger.error(f"리스크 알림 생성 실패: {e}")

    def get_risk_summary(self) -> Dict[str, Any]:
        """현재 리스크 상황 요약"""
        open_trades = self.db.get_open_trades()
        unresolved_alerts = self.db.get_unresolved_alerts()

        # 오늘 성과
        performance = self.db.get_performance_history(days=1)
        today_performance = performance[0] if performance else {}

        total_pnl = today_performance.get('total_pnl', 0) or 0
        net_pnl = today_performance.get('net_pnl', 0) or 0

        summary = {
            'timestamp': datetime.now(),
            'open_positions': len(open_trades),
            'max_positions': self.max_positions,
            'position_utilization': len(open_trades) / self.max_positions if self.max_positions > 0 else 0,
            'today_pnl': net_pnl,
            'daily_loss_pct': abs(net_pnl) / self.initial_balance if net_pnl < 0 else 0,
            'daily_loss_limit': self.max_daily_loss,
            'unresolved_alerts': len(unresolved_alerts),
            'critical_alerts': len([a for a in unresolved_alerts if a.get('severity') == 'CRITICAL']),
            'can_trade': self.check_can_open_position()[0]
        }

        return summary


if __name__ == "__main__":
    # 테스트 코드
    risk_manager = RiskManager(initial_balance=10000.0)

    # 포지션 오픈 가능 체크
    can_open, reason = risk_manager.check_can_open_position()
    print(f"포지션 오픈 가능: {can_open}, 사유: {reason}")

    # 포지션 사이즈 계산
    test_signal = {'symbol': 'BTC/USDT', 'side': 'LONG'}
    position_size = risk_manager.calculate_position_size(test_signal)
    print(f"포지션 사이즈: {position_size} USDT")

    # 레버리지 결정
    test_signal['consensus_count'] = 5
    leverage = risk_manager.determine_leverage(test_signal)
    print(f"레버리지: {leverage}x")

    # 손절/익절 가격 계산
    entry_price = 50000
    stop_loss = risk_manager.calculate_stop_loss_price(entry_price, 'LONG')
    take_profit = risk_manager.calculate_take_profit_price(entry_price, 'LONG')
    print(f"진입가: {entry_price}, 손절가: {stop_loss:.2f}, 익절가: {take_profit:.2f}")

    # 리스크 요약
    summary = risk_manager.get_risk_summary()
    print(f"\n리스크 요약:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
