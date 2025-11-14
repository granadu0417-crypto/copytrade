"""
설정 파일 로더 모듈
YAML 설정 파일과 환경 변수를 로드하여 통합 관리
"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


class ConfigLoader:
    """설정 파일 로더 클래스"""

    def __init__(self, config_path: str = "./config.yaml", env_path: str = ".env"):
        """
        Args:
            config_path: YAML 설정 파일 경로
            env_path: 환경 변수 파일 경로
        """
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        self.config: Dict[str, Any] = {}

        # 환경 변수 로드
        if self.env_path.exists():
            load_dotenv(self.env_path)

        # 설정 파일 로드
        self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """YAML 설정 파일 로드"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 환경 변수로 API 키 등 민감 정보 덮어쓰기
        self._override_with_env()

        return self.config

    def _override_with_env(self):
        """환경 변수로 설정 덮어쓰기"""
        # 시스템 모드
        if os.getenv('MODE'):
            self.config['system']['mode'] = os.getenv('MODE')

        if os.getenv('DEBUG'):
            self.config['system']['debug'] = os.getenv('DEBUG').lower() == 'true'

        # Binance API 키
        if os.getenv('BINANCE_TESTNET_API_KEY'):
            if 'binance' not in self.config:
                self.config['binance'] = {}
            if 'testnet' not in self.config['binance']:
                self.config['binance']['testnet'] = {}
            self.config['binance']['testnet']['api_key'] = os.getenv('BINANCE_TESTNET_API_KEY')

        if os.getenv('BINANCE_TESTNET_SECRET'):
            self.config['binance']['testnet']['secret'] = os.getenv('BINANCE_TESTNET_SECRET')

        if os.getenv('BINANCE_LIVE_API_KEY'):
            if 'live' not in self.config['binance']:
                self.config['binance']['live'] = {}
            self.config['binance']['live']['api_key'] = os.getenv('BINANCE_LIVE_API_KEY')

        if os.getenv('BINANCE_LIVE_SECRET'):
            self.config['binance']['live']['secret'] = os.getenv('BINANCE_LIVE_SECRET')

        # Telegram 설정
        if os.getenv('TELEGRAM_BOT_TOKEN'):
            if 'telegram' not in self.config['notifications']:
                self.config['notifications']['telegram'] = {}
            self.config['notifications']['telegram']['bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN')

        if os.getenv('TELEGRAM_CHAT_ID'):
            self.config['notifications']['telegram']['chat_id'] = os.getenv('TELEGRAM_CHAT_ID')

        # 데이터베이스 경로
        if os.getenv('DATABASE_PATH'):
            self.config['database']['path'] = os.getenv('DATABASE_PATH')

        # 로그 설정
        if os.getenv('LOG_LEVEL'):
            self.config['logging']['level'] = os.getenv('LOG_LEVEL')

        if os.getenv('LOG_FILE'):
            self.config['logging']['log_file'] = os.getenv('LOG_FILE')

    def get(self, *keys, default=None) -> Any:
        """
        중첩된 설정 값 가져오기

        Args:
            *keys: 중첩된 키 (예: 'system', 'mode')
            default: 기본값

        Returns:
            설정 값 또는 기본값
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value

    def get_binance_config(self, mode: str = None) -> Dict[str, Any]:
        """
        Binance API 설정 가져오기

        Args:
            mode: 'testnet' 또는 'live' (None이면 시스템 모드 사용)

        Returns:
            Binance API 설정
        """
        if mode is None:
            mode = self.get('system', 'mode', default='testnet')

        return self.get('binance', mode, default={})

    def get_strategy_config(self) -> Dict[str, Any]:
        """거래 전략 설정 가져오기"""
        return self.get('strategy', default={})

    def get_risk_config(self) -> Dict[str, Any]:
        """리스크 관리 설정 가져오기"""
        return self.get('risk', default={})

    def get_notification_config(self) -> Dict[str, Any]:
        """알림 설정 가져오기"""
        return self.get('notifications', default={})

    def get_database_path(self) -> str:
        """데이터베이스 경로 가져오기"""
        return self.get('database', 'path', default='./data/trading.db')

    def get_logging_config(self) -> Dict[str, Any]:
        """로깅 설정 가져오기"""
        return self.get('logging', default={})

    def is_testnet_mode(self) -> bool:
        """테스트넷 모드 여부 확인"""
        return self.get('system', 'mode', default='testnet') == 'testnet'

    def is_debug_mode(self) -> bool:
        """디버그 모드 여부 확인"""
        return self.get('system', 'debug', default=False)

    def save_config(self):
        """현재 설정을 파일로 저장 (민감 정보 제외)"""
        # 민감 정보가 포함되지 않은 설정만 저장
        safe_config = self.config.copy()

        # API 키 제거
        if 'binance' in safe_config:
            for mode in ['testnet', 'live']:
                if mode in safe_config['binance']:
                    safe_config['binance'][mode].pop('api_key', None)
                    safe_config['binance'][mode].pop('secret', None)

        # Telegram 토큰 제거
        if 'notifications' in safe_config and 'telegram' in safe_config['notifications']:
            safe_config['notifications']['telegram'].pop('bot_token', None)
            safe_config['notifications']['telegram'].pop('chat_id', None)

        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(safe_config, f, default_flow_style=False, allow_unicode=True)


# 전역 설정 인스턴스
_config_instance = None


def get_config() -> ConfigLoader:
    """전역 설정 인스턴스 가져오기"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader()
    return _config_instance


if __name__ == "__main__":
    # 테스트 코드
    config = ConfigLoader()
    print("시스템 모드:", config.get('system', 'mode'))
    print("스크래핑 주기:", config.get('system', 'scraping_interval'))
    print("추적 트레이더 수:", config.get('strategy', 'tracked_traders'))
    print("최소 동의 수:", config.get('strategy', 'min_consensus'))
    print("테스트넷 모드:", config.is_testnet_mode())
    print("디버그 모드:", config.is_debug_mode())
