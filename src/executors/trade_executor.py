"""
거래 실행 모듈
신호를 받아 실제 거래 실행 및 포지션 관리
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from src.executors.binance_client import BinanceClient
from src.managers.risk_manager import RiskManager
from src.database.db_manager import DatabaseManager
from src.utils.logger import get_logger
from src.utils.config_loader import get_config


logger = get_logger()


class TradeExecutor:
    """거래 실행 클래스"""

    def __init__(
        self,
        binance_client: BinanceClient = None,
        risk_manager: RiskManager = None,
        db_manager: DatabaseManager = None,
        testnet: bool = None
    ):
        """
        Args:
            binance_client: Binance API 클라이언트
            risk_manager: 리스크 관리자
            db_manager: 데이터베이스 관리자
            testnet: 테스트넷 사용 여부
        """
        self.config = get_config()
        self.db = db_manager or DatabaseManager(self.config.get_database_path())

        # Binance 클라이언트 초기화
        if binance_client is None:
            if testnet is None:
                testnet = self.config.is_testnet_mode()
            self.client = BinanceClient(testnet=testnet)
        else:
            self.client = binance_client

        # 리스크 매니저 초기화
        if risk_manager is None:
            initial_balance = self.client.get_balance()
            self.risk_manager = RiskManager(
                db_manager=self.db,
                initial_balance=initial_balance
            )
        else:
            self.risk_manager = risk_manager

        # 활성 포지션 추적
        self.active_positions: Dict[str, Dict[str, Any]] = {}

        logger.info("거래 실행기 초기화 완료")

    def execute_signal(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        거래 신호 실행

        Args:
            signal: 거래 신호

        Returns:
            실행된 거래 정보
        """
        try:
            symbol = signal.get('symbol')
            side = signal.get('side', '').upper()
            signal_id = signal.get('signal_id')

            logger.info(f"신호 실행 시작: {symbol} {side} (신호 ID: {signal_id})")

            # 1. 리스크 체크
            can_trade, reason = self.risk_manager.check_can_open_position()
            if not can_trade:
                logger.warning(f"거래 차단: {reason}")
                self.db.update_signal_status(signal_id, 'REJECTED')
                return None

            # 2. 현재 잔고 조회
            current_balance = self.client.get_balance()
            if current_balance <= 0:
                logger.error("잔고 부족")
                self.db.update_signal_status(signal_id, 'REJECTED')
                return None

            # 3. 포지션 사이즈 계산
            position_size_usdt = self.risk_manager.calculate_position_size(
                signal,
                current_balance
            )

            # 4. 레버리지 결정
            leverage = self.risk_manager.determine_leverage(signal)

            # 5. 심볼 포맷 변환 (BTC/USDT -> BTCUSDT)
            binance_symbol = symbol.replace('/', '')

            # 6. 현재 가격 조회
            current_price = self.client.get_current_price(binance_symbol)
            if not current_price:
                logger.error(f"가격 조회 실패: {binance_symbol}")
                self.db.update_signal_status(signal_id, 'REJECTED')
                return None

            # 7. 레버리지 및 마진 타입 설정
            self.client.set_margin_type(binance_symbol, 'ISOLATED')
            self.client.set_leverage(binance_symbol, leverage)

            # 8. 수량 계산
            quantity = self.client.calculate_quantity(
                binance_symbol,
                position_size_usdt,
                leverage,
                current_price
            )

            if quantity <= 0:
                logger.error("수량 계산 오류")
                self.db.update_signal_status(signal_id, 'REJECTED')
                return None

            # 9. 시장가 주문 실행
            order_side = 'BUY' if side == 'LONG' else 'SELL'
            order = self.client.place_market_order(
                symbol=binance_symbol,
                side=order_side,
                quantity=quantity
            )

            if not order:
                logger.error("주문 실행 실패")
                self.db.update_signal_status(signal_id, 'REJECTED')
                return None

            # 10. 실행 가격 (체결 가격)
            executed_price = float(order.get('avgPrice', current_price))

            # 11. 손절/익절 가격 계산
            stop_loss_price = self.risk_manager.calculate_stop_loss_price(
                executed_price,
                side
            )
            take_profit_price = self.risk_manager.calculate_take_profit_price(
                executed_price,
                side
            )

            # 12. 손절/익절 주문 설정
            self._set_stop_loss_take_profit(
                binance_symbol,
                side,
                quantity,
                stop_loss_price,
                take_profit_price
            )

            # 13. 거래 정보 저장
            trade_data = {
                'signal_id': signal_id,
                'order_id': str(order.get('orderId')),
                'symbol': symbol,
                'side': side,
                'entry_price': executed_price,
                'quantity': quantity,
                'leverage': leverage,
                'status': 'OPEN'
            }

            trade_id = self.db.add_trade(trade_data)
            trade_data['id'] = trade_id

            # 14. 신호 상태 업데이트
            self.db.update_signal_status(signal_id, 'EXECUTED')

            # 15. 활성 포지션 추적
            self.active_positions[symbol] = trade_data

            logger.info(
                f"거래 실행 완료: {symbol} {side} | "
                f"진입가: {executed_price:.2f} | "
                f"수량: {quantity} | "
                f"레버리지: {leverage}x | "
                f"손절가: {stop_loss_price:.2f} | "
                f"익절가: {take_profit_price:.2f}"
            )

            return trade_data

        except Exception as e:
            logger.error(f"거래 실행 실패: {e}")
            if signal_id:
                self.db.update_signal_status(signal_id, 'REJECTED')
            return None

    def _set_stop_loss_take_profit(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_loss_price: float,
        take_profit_price: float
    ):
        """손절/익절 주문 설정"""
        try:
            # 손절 주문
            sl_side = 'SELL' if side == 'LONG' else 'BUY'
            self.client.place_stop_loss(
                symbol=symbol,
                side=sl_side,
                quantity=quantity,
                stop_price=stop_loss_price
            )

            # 익절 주문
            tp_side = 'SELL' if side == 'LONG' else 'BUY'
            self.client.place_take_profit(
                symbol=symbol,
                side=tp_side,
                quantity=quantity,
                stop_price=take_profit_price
            )

            logger.info(
                f"손절/익절 설정 완료: {symbol} | "
                f"손절: {stop_loss_price:.2f} | "
                f"익절: {take_profit_price:.2f}"
            )

        except Exception as e:
            logger.error(f"손절/익절 설정 실패: {e}")

    def monitor_positions(self):
        """포지션 모니터링 및 관리"""
        try:
            open_trades = self.db.get_open_trades()

            for trade in open_trades:
                symbol = trade.get('symbol', '').replace('/', '')
                side = trade.get('side')
                entry_price = trade.get('entry_price')
                trade_id = trade.get('id')

                # 현재 가격 조회
                current_price = self.client.get_current_price(symbol)
                if not current_price:
                    continue

                # 리스크 체크
                risk_check = self.risk_manager.check_position_risk(
                    trade,
                    current_price
                )

                # 손절/익절 트리거 확인
                if risk_check.get('should_stop_loss'):
                    logger.warning(f"손절 트리거: {symbol} {side}")
                    self.close_trade(trade_id, current_price, 'STOP_LOSS')

                elif risk_check.get('should_take_profit'):
                    logger.info(f"익절 트리거: {symbol} {side}")
                    self.close_trade(trade_id, current_price, 'TAKE_PROFIT')

                # PnL 업데이트
                pnl_pct = risk_check.get('pnl_pct', 0)
                logger.debug(
                    f"포지션 모니터링: {symbol} {side} | "
                    f"진입: {entry_price:.2f} | "
                    f"현재: {current_price:.2f} | "
                    f"PnL: {pnl_pct:.2f}%"
                )

        except Exception as e:
            logger.error(f"포지션 모니터링 실패: {e}")

    def close_trade(
        self,
        trade_id: int,
        exit_price: float = None,
        reason: str = 'MANUAL'
    ) -> bool:
        """
        거래 청산

        Args:
            trade_id: 거래 ID
            exit_price: 청산 가격 (None이면 현재가)
            reason: 청산 사유

        Returns:
            성공 여부
        """
        try:
            # 거래 정보 조회
            open_trades = self.db.get_open_trades()
            trade = next((t for t in open_trades if t.get('id') == trade_id), None)

            if not trade:
                logger.warning(f"거래를 찾을 수 없음: ID {trade_id}")
                return False

            symbol = trade.get('symbol', '').replace('/', '')
            entry_price = trade.get('entry_price')
            quantity = trade.get('quantity')
            leverage = trade.get('leverage', 1)
            side = trade.get('side')

            # 청산 가격
            if exit_price is None:
                exit_price = self.client.get_current_price(symbol)

            if not exit_price:
                logger.error(f"가격 조회 실패: {symbol}")
                return False

            # 포지션 청산
            success = self.client.close_position(symbol)

            if success:
                # PnL 계산
                if side == 'LONG':
                    pnl_pct = ((exit_price - entry_price) / entry_price) * leverage
                else:  # SHORT
                    pnl_pct = ((entry_price - exit_price) / entry_price) * leverage

                pnl_usdt = (quantity * entry_price) * pnl_pct / leverage

                # 데이터베이스 업데이트
                self.db.close_trade(trade_id, exit_price, pnl_usdt, reason)

                # 활성 포지션에서 제거
                if trade.get('symbol') in self.active_positions:
                    del self.active_positions[trade.get('symbol')]

                logger.info(
                    f"거래 청산 완료: {symbol} {side} | "
                    f"진입: {entry_price:.2f} | "
                    f"청산: {exit_price:.2f} | "
                    f"PnL: {pnl_pct * 100:.2f}% ({pnl_usdt:.2f} USDT) | "
                    f"사유: {reason}"
                )

                return True
            else:
                logger.error(f"포지션 청산 실패: {symbol}")
                return False

        except Exception as e:
            logger.error(f"거래 청산 실패 (ID {trade_id}): {e}")
            return False

    def close_all_trades(self, reason: str = 'MANUAL') -> int:
        """
        모든 거래 청산

        Args:
            reason: 청산 사유

        Returns:
            청산된 거래 수
        """
        try:
            open_trades = self.db.get_open_trades()
            closed_count = 0

            for trade in open_trades:
                if self.close_trade(trade.get('id'), reason=reason):
                    closed_count += 1
                time.sleep(0.5)  # Rate limit 방지

            logger.info(f"전체 거래 청산 완료: {closed_count}개")
            return closed_count

        except Exception as e:
            logger.error(f"전체 거래 청산 실패: {e}")
            return 0

    def emergency_stop(self) -> bool:
        """
        긴급 정지

        Returns:
            성공 여부
        """
        logger.critical("긴급 정지 실행")

        try:
            # 리스크 매니저 긴급 정지
            self.risk_manager.emergency_stop()

            # 모든 포지션 청산
            success = self.client.close_all_positions()

            # 모든 거래 청산 처리
            if success:
                self.close_all_trades(reason='EMERGENCY')
                logger.critical("긴급 정지 완료: 모든 포지션 청산됨")
                return True
            else:
                logger.error("긴급 정지 실패")
                return False

        except Exception as e:
            logger.error(f"긴급 정지 실행 중 오류: {e}")
            return False

    def sync_positions(self):
        """Binance 실제 포지션과 DB 동기화"""
        try:
            # Binance 실제 포지션 조회
            binance_positions = self.client.get_position()

            # DB 오픈 거래 조회
            db_trades = self.db.get_open_trades()

            # Binance에는 있지만 DB에 없는 포지션 체크
            binance_symbols = {pos.get('symbol') for pos in binance_positions}
            db_symbols = {trade.get('symbol', '').replace('/', '') for trade in db_trades}

            # 불일치 로그
            only_in_binance = binance_symbols - db_symbols
            only_in_db = db_symbols - binance_symbols

            if only_in_binance:
                logger.warning(f"Binance에만 있는 포지션: {only_in_binance}")

            if only_in_db:
                logger.warning(f"DB에만 있는 거래: {only_in_db}")
                # DB에만 있으면 청산된 것으로 간주
                for symbol in only_in_db:
                    trade = next(
                        (t for t in db_trades if t.get('symbol', '').replace('/', '') == symbol),
                        None
                    )
                    if trade:
                        current_price = self.client.get_current_price(symbol)
                        if current_price:
                            self.close_trade(trade.get('id'), current_price, 'AUTO_SYNC')

            logger.info("포지션 동기화 완료")

        except Exception as e:
            logger.error(f"포지션 동기화 실패: {e}")


if __name__ == "__main__":
    # 테스트 코드
    try:
        executor = TradeExecutor(testnet=True)

        # 테스트 신호
        test_signal = {
            'signal_id': 'test_signal_001',
            'symbol': 'BTC/USDT',
            'side': 'LONG',
            'consensus_count': 5,
            'avg_entry_price': 50000,
            'avg_leverage': 5
        }

        # 신호 실행 (주의: 실제 Testnet에 주문이 들어갑니다!)
        # trade = executor.execute_signal(test_signal)
        # if trade:
        #     print(f"거래 실행 완료: {trade}")

        # 포지션 모니터링
        executor.monitor_positions()

        # 포지션 동기화
        executor.sync_positions()

    except Exception as e:
        print(f"테스트 실패: {e}")
