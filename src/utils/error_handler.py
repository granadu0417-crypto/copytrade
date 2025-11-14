"""
에러 처리 및 복구 시스템
재시도 로직, 백업 소스, 자동 복구 기능 제공
"""
import time
import functools
from typing import Callable, Any, Optional, Type, Tuple
from datetime import datetime, timedelta

from src.utils.logger import get_logger
from src.database.db_manager import DatabaseManager
from src.utils.config_loader import get_config


logger = get_logger()


class ErrorHandler:
    """에러 처리 클래스"""

    def __init__(self, db_manager: DatabaseManager = None):
        """
        Args:
            db_manager: 데이터베이스 관리자
        """
        self.config = get_config()
        self.db = db_manager or DatabaseManager(self.config.get_database_path())

        # 스크래핑 설정
        scraping_config = self.config.get('scraping', default={})
        self.max_retries = scraping_config.get('retry_count', 3)
        self.retry_delay = scraping_config.get('retry_delay', 5)  # 초

        # 에러 카운터
        self.error_counts = {}
        self.last_errors = {}

    def retry_on_error(
        self,
        max_retries: int = None,
        delay: float = None,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        backoff: bool = True
    ):
        """
        에러 발생시 재시도하는 데코레이터

        Args:
            max_retries: 최대 재시도 횟수
            delay: 재시도 간 대기 시간 (초)
            exceptions: 처리할 예외 타입 튜플
            backoff: 지수 백오프 사용 여부

        Usage:
            @error_handler.retry_on_error(max_retries=3)
            def my_function():
                # 함수 내용
                pass
        """
        if max_retries is None:
            max_retries = self.max_retries
        if delay is None:
            delay = self.retry_delay

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                last_exception = None

                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)

                    except exceptions as e:
                        last_exception = e

                        if attempt < max_retries:
                            # 대기 시간 계산 (지수 백오프)
                            wait_time = delay * (2 ** attempt) if backoff else delay

                            logger.warning(
                                f"{func.__name__} 실패 (시도 {attempt + 1}/{max_retries + 1}): {e} | "
                                f"{wait_time:.1f}초 후 재시도"
                            )

                            # 에러 로그
                            self._log_error(func.__name__, str(e), attempt + 1)

                            time.sleep(wait_time)
                        else:
                            logger.error(
                                f"{func.__name__} 최종 실패 ({max_retries + 1}회 시도): {e}"
                            )
                            self._log_error(func.__name__, str(e), attempt + 1, final=True)

                # 모든 재시도 실패
                raise last_exception

            return wrapper
        return decorator

    def handle_scraping_error(self, error: Exception, source: str = 'unknown') -> bool:
        """
        스크래핑 에러 처리

        Args:
            error: 발생한 에러
            source: 에러 소스

        Returns:
            복구 성공 여부
        """
        error_type = type(error).__name__
        error_msg = str(error)

        logger.error(f"스크래핑 에러 발생 ({source}): {error_type} - {error_msg}")

        # 에러 카운트 증가
        error_key = f"scraping_{source}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_errors[error_key] = datetime.now()

        # 데이터베이스에 로그 저장
        self.db.add_log(
            level='ERROR',
            module='LeaderboardScraper',
            message=f'스크래핑 에러: {error_type}',
            details={'source': source, 'error': error_msg}
        )

        # 에러가 너무 자주 발생하면 알림
        if self.error_counts.get(error_key, 0) >= 5:
            logger.critical(f"스크래핑 에러 {error_key} 5회 이상 발생!")
            self.db.add_risk_alert(
                'SCRAPING_ERROR',
                'CRITICAL',
                f'{source} 스크래핑 반복 실패',
                {'count': self.error_counts[error_key]}
            )
            return False

        return True

    def handle_api_error(self, error: Exception, api_name: str = 'binance') -> bool:
        """
        API 에러 처리

        Args:
            error: 발생한 에러
            api_name: API 이름

        Returns:
            복구 성공 여부
        """
        error_type = type(error).__name__
        error_msg = str(error)

        logger.error(f"API 에러 발생 ({api_name}): {error_type} - {error_msg}")

        # Rate Limit 체크
        if 'rate limit' in error_msg.lower() or '429' in error_msg:
            logger.warning(f"{api_name} Rate Limit 도달 - 60초 대기")
            time.sleep(60)
            return True

        # 연결 오류
        if 'connection' in error_msg.lower() or 'timeout' in error_msg.lower():
            logger.warning(f"{api_name} 연결 오류 - 재시도 가능")
            return True

        # 인증 오류
        if 'auth' in error_msg.lower() or '401' in error_msg or '403' in error_msg:
            logger.critical(f"{api_name} 인증 오류 - API 키 확인 필요!")
            self.db.add_risk_alert(
                'API_AUTH_ERROR',
                'CRITICAL',
                f'{api_name} API 인증 실패',
                {'error': error_msg}
            )
            return False

        # 에러 카운트
        error_key = f"api_{api_name}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        # 데이터베이스에 로그 저장
        self.db.add_log(
            level='ERROR',
            module='BinanceClient',
            message=f'API 에러: {error_type}',
            details={'api': api_name, 'error': error_msg}
        )

        return True

    def handle_network_error(self, error: Exception) -> bool:
        """
        네트워크 에러 처리

        Args:
            error: 발생한 에러

        Returns:
            복구 성공 여부
        """
        error_msg = str(error)

        logger.error(f"네트워크 에러 발생: {error_msg}")

        # 연결 상태 확인
        # TODO: 실제 네트워크 연결 체크 로직 추가

        # 자동 재연결 시도
        logger.info("네트워크 재연결 시도 중...")
        time.sleep(5)

        # 데이터베이스에 로그 저장
        self.db.add_log(
            level='ERROR',
            module='Network',
            message='네트워크 오류',
            details={'error': error_msg}
        )

        return True

    def handle_database_error(self, error: Exception, operation: str = 'unknown') -> bool:
        """
        데이터베이스 에러 처리

        Args:
            error: 발생한 에러
            operation: 작업 종류

        Returns:
            복구 성공 여부
        """
        error_type = type(error).__name__
        error_msg = str(error)

        logger.error(f"데이터베이스 에러 발생 ({operation}): {error_type} - {error_msg}")

        # 락 오류 처리
        if 'locked' in error_msg.lower():
            logger.warning("데이터베이스 락 감지 - 재시도")
            time.sleep(1)
            return True

        # 디스크 공간 오류
        if 'disk' in error_msg.lower() or 'space' in error_msg.lower():
            logger.critical("디스크 공간 부족!")
            self.db.add_risk_alert(
                'DISK_SPACE_ERROR',
                'CRITICAL',
                '디스크 공간 부족',
                {'error': error_msg}
            )
            return False

        return True

    def _log_error(
        self,
        function_name: str,
        error_msg: str,
        attempt: int,
        final: bool = False
    ):
        """에러 로그 기록"""
        try:
            level = 'ERROR' if final else 'WARNING'
            self.db.add_log(
                level=level,
                module='ErrorHandler',
                message=f'{function_name} 실패 (시도 {attempt})',
                details={'error': error_msg, 'final': final}
            )
        except Exception as e:
            # 로그 저장 실패는 무시
            logger.warning(f"에러 로그 저장 실패: {e}")

    def check_error_threshold(self, error_key: str, threshold: int = 10) -> bool:
        """
        에러 임계값 체크

        Args:
            error_key: 에러 키
            threshold: 임계값

        Returns:
            임계값 초과 여부
        """
        count = self.error_counts.get(error_key, 0)
        if count >= threshold:
            logger.critical(f"에러 임계값 초과: {error_key} ({count}회)")
            return True
        return False

    def reset_error_count(self, error_key: str = None):
        """
        에러 카운트 리셋

        Args:
            error_key: 리셋할 에러 키 (None이면 전체 리셋)
        """
        if error_key:
            if error_key in self.error_counts:
                del self.error_counts[error_key]
            if error_key in self.last_errors:
                del self.last_errors[error_key]
            logger.info(f"에러 카운트 리셋: {error_key}")
        else:
            self.error_counts.clear()
            self.last_errors.clear()
            logger.info("모든 에러 카운트 리셋")

    def get_error_summary(self) -> dict:
        """에러 요약 정보 반환"""
        return {
            'total_errors': sum(self.error_counts.values()),
            'error_counts': self.error_counts.copy(),
            'last_errors': {
                key: value.isoformat()
                for key, value in self.last_errors.items()
            }
        }

    def auto_recover(self, error: Exception, context: dict = None) -> bool:
        """
        자동 복구 시도

        Args:
            error: 발생한 에러
            context: 에러 컨텍스트 정보

        Returns:
            복구 성공 여부
        """
        error_type = type(error).__name__

        logger.info(f"자동 복구 시도: {error_type}")

        try:
            # 에러 타입별 복구 로직
            if 'Network' in error_type or 'Connection' in error_type:
                return self.handle_network_error(error)

            elif 'API' in error_type or 'Binance' in error_type:
                api_name = context.get('api_name', 'binance') if context else 'binance'
                return self.handle_api_error(error, api_name)

            elif 'Database' in error_type or 'SQL' in error_type:
                operation = context.get('operation', 'unknown') if context else 'unknown'
                return self.handle_database_error(error, operation)

            else:
                logger.warning(f"알 수 없는 에러 타입: {error_type}")
                return False

        except Exception as e:
            logger.error(f"자동 복구 실패: {e}")
            return False


# 전역 에러 핸들러 인스턴스
_error_handler_instance = None


def get_error_handler() -> ErrorHandler:
    """전역 에러 핸들러 인스턴스 가져오기"""
    global _error_handler_instance
    if _error_handler_instance is None:
        _error_handler_instance = ErrorHandler()
    return _error_handler_instance


if __name__ == "__main__":
    # 테스트 코드
    error_handler = ErrorHandler()

    # 재시도 데코레이터 테스트
    @error_handler.retry_on_error(max_retries=3, delay=1)
    def test_function():
        import random
        if random.random() < 0.7:  # 70% 확률로 실패
            raise Exception("랜덤 실패")
        return "성공!"

    try:
        result = test_function()
        print(f"결과: {result}")
    except Exception as e:
        print(f"최종 실패: {e}")

    # 에러 요약
    summary = error_handler.get_error_summary()
    print(f"\n에러 요약:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
