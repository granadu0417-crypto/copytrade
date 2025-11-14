"""
Binance API 클라이언트 모듈
Testnet 및 Live 환경 지원
"""
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from typing import Dict, Any, Optional, List
from decimal import Decimal
import time

from src.utils.logger import get_logger
from src.utils.config_loader import get_config


logger = get_logger()


class BinanceClient:
    """Binance API 클라이언트 래퍼"""

    def __init__(self, testnet: bool = None):
        """
        Args:
            testnet: 테스트넷 사용 여부 (None이면 config에서 읽음)
        """
        self.config = get_config()

        # 테스트넷 모드 결정
        if testnet is None:
            self.testnet = self.config.is_testnet_mode()
        else:
            self.testnet = testnet

        # API 설정 로드
        mode = 'testnet' if self.testnet else 'live'
        binance_config = self.config.get_binance_config(mode)

        self.api_key = binance_config.get('api_key', '')
        self.api_secret = binance_config.get('secret', '')

        if not self.api_key or not self.api_secret:
            raise ValueError(
                f"Binance API 키가 설정되지 않았습니다 (모드: {mode}). "
                ".env 파일을 확인하세요."
            )

        # 클라이언트 초기화
        self.client = None
        self._initialize_client()

        logger.info(f"Binance 클라이언트 초기화 완료 (모드: {'TESTNET' if self.testnet else 'LIVE'})")

    def _initialize_client(self):
        """Binance 클라이언트 초기화"""
        try:
            if self.testnet:
                # Testnet 설정
                self.client = Client(
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                    testnet=True
                )
                # Testnet URL 설정
                self.client.API_URL = 'https://testnet.binancefuture.com'
            else:
                # Live 설정
                self.client = Client(
                    api_key=self.api_key,
                    api_secret=self.api_secret
                )

            # 연결 테스트
            self.client.ping()
            logger.info("Binance API 연결 테스트 성공")

        except Exception as e:
            logger.error(f"Binance 클라이언트 초기화 실패: {e}")
            raise

    def get_account_info(self) -> Dict[str, Any]:
        """계정 정보 조회"""
        try:
            account = self.client.futures_account()
            return {
                'balance': float(account.get('totalWalletBalance', 0)),
                'available_balance': float(account.get('availableBalance', 0)),
                'unrealized_pnl': float(account.get('totalUnrealizedProfit', 0)),
                'margin_balance': float(account.get('totalMarginBalance', 0)),
                'positions': account.get('positions', [])
            }
        except BinanceAPIException as e:
            logger.error(f"계정 정보 조회 실패: {e}")
            raise

    def get_balance(self) -> float:
        """사용 가능한 잔고 조회 (USDT)"""
        try:
            account = self.get_account_info()
            return account.get('available_balance', 0)
        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}")
            return 0

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """레버리지 설정"""
        try:
            self.client.futures_change_leverage(
                symbol=symbol,
                leverage=leverage
            )
            logger.info(f"레버리지 설정: {symbol} {leverage}x")
            return True
        except BinanceAPIException as e:
            logger.error(f"레버리지 설정 실패 ({symbol} {leverage}x): {e}")
            return False

    def set_margin_type(self, symbol: str, margin_type: str = 'ISOLATED') -> bool:
        """
        마진 타입 설정

        Args:
            symbol: 거래 심볼
            margin_type: ISOLATED 또는 CROSSED
        """
        try:
            self.client.futures_change_margin_type(
                symbol=symbol,
                marginType=margin_type
            )
            logger.info(f"마진 타입 설정: {symbol} {margin_type}")
            return True
        except BinanceAPIException as e:
            # 이미 설정된 경우 에러 무시
            if 'No need to change margin type' in str(e):
                logger.debug(f"마진 타입 이미 설정됨: {symbol} {margin_type}")
                return True
            logger.error(f"마진 타입 설정 실패 ({symbol} {margin_type}): {e}")
            return False

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """심볼 정보 조회"""
        try:
            exchange_info = self.client.futures_exchange_info()
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol:
                    return s
            return None
        except Exception as e:
            logger.error(f"심볼 정보 조회 실패 ({symbol}): {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재 시장 가격 조회"""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"가격 조회 실패 ({symbol}): {e}")
            return None

    def calculate_quantity(
        self,
        symbol: str,
        usdt_amount: float,
        leverage: int,
        price: float = None
    ) -> float:
        """
        포지션 수량 계산

        Args:
            symbol: 거래 심볼
            usdt_amount: USDT 금액
            leverage: 레버리지
            price: 진입 가격 (None이면 현재가)

        Returns:
            계산된 수량
        """
        if price is None:
            price = self.get_current_price(symbol)

        if not price:
            raise ValueError(f"가격 조회 실패: {symbol}")

        # 레버리지 적용한 수량 계산
        quantity = (usdt_amount * leverage) / price

        # 심볼 정보에서 수량 정밀도 확인
        symbol_info = self.get_symbol_info(symbol)
        if symbol_info:
            for filter in symbol_info.get('filters', []):
                if filter['filterType'] == 'LOT_SIZE':
                    step_size = float(filter['stepSize'])
                    # stepSize에 맞게 반올림
                    precision = len(str(step_size).rstrip('0').split('.')[-1])
                    quantity = round(quantity, precision)
                    break

        logger.debug(
            f"수량 계산: {symbol} | "
            f"금액: {usdt_amount} USDT | "
            f"레버리지: {leverage}x | "
            f"가격: {price} | "
            f"수량: {quantity}"
        )

        return quantity

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        reduce_only: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        시장가 주문

        Args:
            symbol: 거래 심볼
            side: BUY 또는 SELL
            quantity: 수량
            reduce_only: 포지션 감소만 허용

        Returns:
            주문 정보
        """
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity,
                reduceOnly=reduce_only
            )

            logger.info(
                f"시장가 주문 실행: {symbol} {side} {quantity} | "
                f"주문 ID: {order.get('orderId')}"
            )

            return order

        except BinanceOrderException as e:
            logger.error(f"주문 실패 ({symbol} {side} {quantity}): {e}")
            raise
        except Exception as e:
            logger.error(f"주문 처리 중 오류 ({symbol}): {e}")
            raise

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = 'GTC'
    ) -> Optional[Dict[str, Any]]:
        """
        지정가 주문

        Args:
            symbol: 거래 심볼
            side: BUY 또는 SELL
            quantity: 수량
            price: 지정 가격
            time_in_force: GTC, IOC, FOK
        """
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                quantity=quantity,
                price=price,
                timeInForce=time_in_force
            )

            logger.info(
                f"지정가 주문 실행: {symbol} {side} {quantity} @ {price} | "
                f"주문 ID: {order.get('orderId')}"
            )

            return order

        except Exception as e:
            logger.error(f"지정가 주문 실패: {e}")
            raise

    def place_stop_loss(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        손절 주문 (Stop Market)

        Args:
            symbol: 거래 심볼
            side: BUY 또는 SELL
            quantity: 수량
            stop_price: 손절 가격
        """
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='STOP_MARKET',
                quantity=quantity,
                stopPrice=stop_price
            )

            logger.info(
                f"손절 주문 설정: {symbol} {side} {quantity} @ {stop_price} | "
                f"주문 ID: {order.get('orderId')}"
            )

            return order

        except Exception as e:
            logger.error(f"손절 주문 실패: {e}")
            raise

    def place_take_profit(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        익절 주문 (Take Profit Market)

        Args:
            symbol: 거래 심볼
            side: BUY 또는 SELL
            quantity: 수량
            stop_price: 익절 가격
        """
        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='TAKE_PROFIT_MARKET',
                quantity=quantity,
                stopPrice=stop_price
            )

            logger.info(
                f"익절 주문 설정: {symbol} {side} {quantity} @ {stop_price} | "
                f"주문 ID: {order.get('orderId')}"
            )

            return order

        except Exception as e:
            logger.error(f"익절 주문 실패: {e}")
            raise

    def cancel_order(self, symbol: str, order_id: int) -> bool:
        """주문 취소"""
        try:
            self.client.futures_cancel_order(
                symbol=symbol,
                orderId=order_id
            )
            logger.info(f"주문 취소: {symbol} 주문 ID: {order_id}")
            return True
        except Exception as e:
            logger.error(f"주문 취소 실패 ({symbol} {order_id}): {e}")
            return False

    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """미체결 주문 조회"""
        try:
            if symbol:
                orders = self.client.futures_get_open_orders(symbol=symbol)
            else:
                orders = self.client.futures_get_open_orders()
            return orders
        except Exception as e:
            logger.error(f"미체결 주문 조회 실패: {e}")
            return []

    def get_position(self, symbol: str = None) -> List[Dict[str, Any]]:
        """포지션 조회"""
        try:
            positions = self.client.futures_position_information(symbol=symbol)
            # 실제 포지션만 필터링 (수량이 0이 아닌 것)
            active_positions = [
                pos for pos in positions
                if float(pos.get('positionAmt', 0)) != 0
            ]
            return active_positions
        except Exception as e:
            logger.error(f"포지션 조회 실패: {e}")
            return []

    def close_position(self, symbol: str) -> bool:
        """포지션 전체 청산"""
        try:
            positions = self.get_position(symbol)
            if not positions:
                logger.info(f"청산할 포지션 없음: {symbol}")
                return True

            for pos in positions:
                position_amt = float(pos.get('positionAmt', 0))
                if position_amt == 0:
                    continue

                # 포지션 방향에 따라 반대 주문
                side = 'SELL' if position_amt > 0 else 'BUY'
                quantity = abs(position_amt)

                self.place_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    reduce_only=True
                )

            logger.info(f"포지션 청산 완료: {symbol}")
            return True

        except Exception as e:
            logger.error(f"포지션 청산 실패 ({symbol}): {e}")
            return False

    def close_all_positions(self) -> bool:
        """모든 포지션 청산"""
        try:
            positions = self.get_position()

            for pos in positions:
                symbol = pos.get('symbol')
                if symbol:
                    self.close_position(symbol)
                    time.sleep(0.5)  # Rate limit 방지

            logger.info("모든 포지션 청산 완료")
            return True

        except Exception as e:
            logger.error(f"전체 포지션 청산 실패: {e}")
            return False


if __name__ == "__main__":
    # 테스트 코드
    try:
        # Testnet 클라이언트 초기화
        client = BinanceClient(testnet=True)

        # 계정 정보
        account = client.get_account_info()
        print(f"잔고: {account.get('balance')} USDT")
        print(f"사용 가능: {account.get('available_balance')} USDT")

        # 현재 가격 조회
        btc_price = client.get_current_price('BTCUSDT')
        print(f"BTC 가격: {btc_price}")

        # 포지션 조회
        positions = client.get_position()
        print(f"활성 포지션: {len(positions)}개")

    except Exception as e:
        print(f"테스트 실패: {e}")
