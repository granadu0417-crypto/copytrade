"""
신호 분석 엔진 모듈
다수 트레이더의 포지션을 분석하여 거래 신호 생성
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import json

from src.utils.logger import get_logger
from src.utils.config_loader import get_config
from src.database.db_manager import DatabaseManager


logger = get_logger()


class SignalAnalyzer:
    """거래 신호 분석 클래스"""

    def __init__(self, db_manager: DatabaseManager = None):
        """
        Args:
            db_manager: 데이터베이스 관리자 인스턴스
        """
        self.config = get_config()
        self.db = db_manager or DatabaseManager(self.config.get_database_path())

        # 전략 설정 로드
        strategy_config = self.config.get_strategy_config()
        self.min_consensus = strategy_config.get('min_consensus', 3)
        self.time_window = strategy_config.get('time_window', 5)  # 분
        self.tracked_traders = strategy_config.get('tracked_traders', 15)

        # 필터 설정 로드
        filters = self.config.get('filters', default={})
        self.min_roi_7d = filters.get('min_roi_7d', 10.0)
        self.min_win_rate = filters.get('min_win_rate', 50.0)
        self.min_followers = filters.get('min_followers', 100)
        self.blacklist_symbols = set(filters.get('blacklist_symbols', []))
        self.whitelist_symbols = set(filters.get('whitelist_symbols', []))

    def analyze_signals(self, positions: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        포지션 데이터를 분석하여 거래 신호 생성

        Args:
            positions: 포지션 리스트 (None이면 DB에서 조회)

        Returns:
            생성된 거래 신호 리스트
        """
        try:
            # 포지션 데이터 가져오기
            if positions is None:
                positions = self.db.get_recent_positions(minutes=self.time_window)

            if not positions:
                logger.info("분석할 포지션이 없습니다")
                return []

            logger.info(f"{len(positions)}개의 최근 포지션 분석 시작")

            # 시간 윈도우 필터링
            recent_positions = self._filter_recent_positions(positions)

            if not recent_positions:
                logger.info(f"최근 {self.time_window}분 내 포지션이 없습니다")
                return []

            # 코인-방향별 그룹화
            grouped = self._group_by_symbol_direction(recent_positions)

            # 거래 신호 생성
            signals = []
            for key, group in grouped.items():
                if len(group) >= self.min_consensus:
                    signal = self._create_signal(key, group)
                    if signal:
                        signals.append(signal)
                        # 데이터베이스에 저장
                        self.db.add_signal(signal)

            logger.info(f"{len(signals)}개의 거래 신호 생성 완료")
            return signals

        except Exception as e:
            logger.error(f"신호 분석 실패: {e}")
            return []

    def _filter_recent_positions(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """시간 윈도우 내 포지션만 필터링"""
        cutoff_time = datetime.now() - timedelta(minutes=self.time_window)
        recent = []

        for pos in positions:
            detected_at = pos.get('detected_at')

            # 문자열인 경우 datetime으로 변환
            if isinstance(detected_at, str):
                detected_at = datetime.fromisoformat(detected_at.replace('Z', '+00:00'))

            if detected_at and detected_at >= cutoff_time:
                recent.append(pos)

        logger.info(
            f"최근 {self.time_window}분 내 포지션: {len(recent)}개 "
            f"(전체: {len(positions)}개)"
        )
        return recent

    def _group_by_symbol_direction(
        self,
        positions: List[Dict[str, Any]]
    ) -> Dict[tuple, List[Dict[str, Any]]]:
        """코인-방향별로 포지션 그룹화"""
        grouped = defaultdict(list)

        for pos in positions:
            symbol = pos.get('symbol', '').upper()
            side = pos.get('side', '').upper()

            # 블랙리스트/화이트리스트 체크
            if not self._is_symbol_allowed(symbol):
                continue

            # 유효성 체크
            if not symbol or not side:
                continue

            key = (symbol, side)
            grouped[key].append(pos)

        # 동의 수가 많은 순으로 정렬
        sorted_groups = dict(
            sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)
        )

        return sorted_groups

    def _is_symbol_allowed(self, symbol: str) -> bool:
        """심볼이 거래 허용 대상인지 확인"""
        # 화이트리스트가 있으면 화이트리스트만 허용
        if self.whitelist_symbols:
            return symbol in self.whitelist_symbols

        # 블랙리스트 체크
        if symbol in self.blacklist_symbols:
            return False

        return True

    def _create_signal(
        self,
        key: tuple,
        positions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """거래 신호 생성"""
        symbol, side = key
        consensus_count = len(positions)

        # 평균 진입가 계산
        entry_prices = [
            pos.get('entry_price', 0)
            for pos in positions
            if pos.get('entry_price')
        ]
        avg_entry_price = sum(entry_prices) / len(entry_prices) if entry_prices else None

        # 평균 레버리지 계산
        leverages = [
            pos.get('leverage', 1)
            for pos in positions
            if pos.get('leverage')
        ]
        avg_leverage = sum(leverages) / len(leverages) if leverages else 1

        # 트레이더 ID 목록
        trader_ids = [pos.get('trader_id') for pos in positions if pos.get('trader_id')]

        # 신호 ID 생성 (고유값)
        signal_id = self._generate_signal_id(symbol, side, datetime.now())

        signal = {
            'signal_id': signal_id,
            'symbol': symbol,
            'side': side,
            'consensus_count': consensus_count,
            'avg_entry_price': avg_entry_price,
            'avg_leverage': avg_leverage,
            'trader_ids': trader_ids,
            'status': 'PENDING',
            'created_at': datetime.now()
        }

        logger.info(
            f"신호 생성: {symbol} {side} | "
            f"동의 수: {consensus_count} | "
            f"평균 진입가: {avg_entry_price:.2f if avg_entry_price else 0} | "
            f"평균 레버리지: {avg_leverage:.1f}"
        )

        return signal

    @staticmethod
    def _generate_signal_id(symbol: str, side: str, timestamp: datetime) -> str:
        """신호 고유 ID 생성"""
        data = f"{symbol}_{side}_{timestamp.isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]

    def filter_quality_traders(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        품질 기준을 만족하는 트레이더의 포지션만 필터링

        Args:
            positions: 포지션 리스트

        Returns:
            필터링된 포지션 리스트
        """
        filtered = []

        for pos in positions:
            trader_id = pos.get('trader_id')
            if not trader_id:
                continue

            # 트레이더 정보 조회
            trader = self.db.get_trader_by_uid(str(trader_id))
            if not trader:
                continue

            # 품질 기준 체크
            roi_7d = trader.get('roi_7d', 0) or 0
            win_rate = trader.get('win_rate', 0) or 0
            followers = trader.get('followers', 0) or 0

            if (roi_7d >= self.min_roi_7d and
                win_rate >= self.min_win_rate and
                followers >= self.min_followers):
                filtered.append(pos)

        logger.info(
            f"품질 필터링: {len(filtered)}개 포지션 선택 "
            f"(전체: {len(positions)}개)"
        )

        return filtered

    def get_signal_strength(self, signal: Dict[str, Any]) -> str:
        """
        신호 강도 평가

        Args:
            signal: 거래 신호

        Returns:
            강도 레벨 ('WEAK', 'MEDIUM', 'STRONG')
        """
        consensus_count = signal.get('consensus_count', 0)

        if consensus_count >= self.min_consensus * 2:
            return 'STRONG'
        elif consensus_count >= self.min_consensus * 1.5:
            return 'MEDIUM'
        else:
            return 'WEAK'

    def analyze_position_consensus(
        self,
        symbol: str,
        side: str
    ) -> Dict[str, Any]:
        """
        특정 심볼-방향에 대한 현재 컨센서스 분석

        Args:
            symbol: 거래 심볼
            side: 포지션 방향 (LONG/SHORT)

        Returns:
            컨센서스 분석 결과
        """
        # 최근 포지션 조회
        positions = self.db.get_recent_positions(minutes=self.time_window)

        # 해당 심볼-방향 필터링
        matching = [
            pos for pos in positions
            if pos.get('symbol', '').upper() == symbol.upper()
            and pos.get('side', '').upper() == side.upper()
        ]

        consensus_count = len(matching)
        trader_ids = [pos.get('trader_id') for pos in matching]

        return {
            'symbol': symbol,
            'side': side,
            'consensus_count': consensus_count,
            'trader_ids': trader_ids,
            'meets_threshold': consensus_count >= self.min_consensus,
            'timestamp': datetime.now()
        }


if __name__ == "__main__":
    # 테스트 코드
    analyzer = SignalAnalyzer()

    # 테스트 포지션 데이터
    test_positions = [
        {
            'trader_id': 1,
            'symbol': 'BTC/USDT',
            'side': 'LONG',
            'entry_price': 50000,
            'leverage': 5,
            'detected_at': datetime.now()
        },
        {
            'trader_id': 2,
            'symbol': 'BTC/USDT',
            'side': 'LONG',
            'entry_price': 50100,
            'leverage': 3,
            'detected_at': datetime.now()
        },
        {
            'trader_id': 3,
            'symbol': 'BTC/USDT',
            'side': 'LONG',
            'entry_price': 49900,
            'leverage': 7,
            'detected_at': datetime.now()
        },
    ]

    signals = analyzer.analyze_signals(test_positions)
    print(f"생성된 신호: {len(signals)}개")
    for signal in signals:
        print(f"- {signal}")
