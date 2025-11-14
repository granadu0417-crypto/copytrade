"""
메인 컨트롤러
모든 모듈을 통합하여 자동 거래 시스템 실행
"""
import asyncio
from typing import Optional
from datetime import datetime, timedelta
import signal
import sys

from src.utils.logger import get_logger
from src.utils.config_loader import get_config
from src.utils.error_handler import get_error_handler
from src.database.db_manager import DatabaseManager
from src.scrapers.leaderboard_scraper import LeaderboardScraper
from src.analyzers.signal_analyzer import SignalAnalyzer
from src.managers.risk_manager import RiskManager
from src.executors.binance_client import BinanceClient
from src.executors.trade_executor import TradeExecutor
from src.notifications.telegram_bot import get_telegram_notifier


logger = get_logger()


class TradingSystemController:
    """거래 시스템 메인 컨트롤러"""

    def __init__(self):
        """초기화"""
        self.config = get_config()
        self.error_handler = get_error_handler()

        # 상태
        self.is_running = False
        self.started_at: Optional[datetime] = None

        # 모듈 인스턴스
        self.db: Optional[DatabaseManager] = None
        self.scraper: Optional[LeaderboardScraper] = None
        self.signal_analyzer: Optional[SignalAnalyzer] = None
        self.risk_manager: Optional[RiskManager] = None
        self.binance_client: Optional[BinanceClient] = None
        self.trade_executor: Optional[TradeExecutor] = None
        self.telegram = get_telegram_notifier()

        # 설정
        self.scraping_interval = self.config.get('system', 'scraping_interval', default=60)  # 초

        logger.info("거래 시스템 컨트롤러 초기화")

    async def initialize(self):
        """모든 모듈 초기화"""
        try:
            logger.info("=== 시스템 초기화 시작 ===")

            # 데이터베이스 초기화
            logger.info("데이터베이스 초기화...")
            db_path = self.config.get_database_path()
            self.db = DatabaseManager(db_path)
            self.db.initialize_database()

            # Binance 클라이언트 초기화
            logger.info("Binance 클라이언트 초기화...")
            testnet = self.config.is_testnet_mode()
            self.binance_client = BinanceClient(testnet=testnet)

            # 리스크 매니저 초기화
            logger.info("리스크 매니저 초기화...")
            initial_balance = self.binance_client.get_balance()
            self.risk_manager = RiskManager(
                db_manager=self.db,
                initial_balance=initial_balance
            )

            # 거래 실행기 초기화
            logger.info("거래 실행기 초기화...")
            self.trade_executor = TradeExecutor(
                binance_client=self.binance_client,
                risk_manager=self.risk_manager,
                db_manager=self.db
            )

            # 신호 분석기 초기화
            logger.info("신호 분석기 초기화...")
            self.signal_analyzer = SignalAnalyzer(db_manager=self.db)

            # 스크래퍼 초기화
            logger.info("스크래퍼 초기화...")
            self.scraper = LeaderboardScraper(db_manager=self.db)
            await self.scraper.initialize()

            # 텔레그램 봇 시작
            if self.telegram.enabled:
                logger.info("텔레그램 봇 시작...")
                await self.telegram.start_bot()

            logger.info("=== 시스템 초기화 완료 ===")

            # 초기화 완료 알림
            if self.telegram.enabled:
                await self.telegram.send_message(
                    "✅ 시스템 초기화 완료\n카피트레이딩 시스템이 준비되었습니다."
                )

        except Exception as e:
            logger.error(f"시스템 초기화 실패: {e}")
            if self.telegram.enabled:
                await self.telegram.notify_error("초기화 실패", str(e))
            raise

    async def start(self):
        """거래 시스템 시작"""
        if self.is_running:
            logger.warning("이미 실행 중입니다")
            return

        try:
            self.is_running = True
            self.started_at = datetime.now()

            logger.info("=== 거래 시스템 시작 ===")

            # 시작 알림
            if self.telegram.enabled:
                await self.telegram.send_message(
                    "🚀 거래 시스템 시작\n자동 거래가 시작되었습니다."
                )

            # 메인 루프 실행
            await self.main_loop()

        except Exception as e:
            logger.error(f"시스템 실행 오류: {e}")
            if self.telegram.enabled:
                await self.telegram.notify_error("시스템 오류", str(e))
        finally:
            self.is_running = False

    async def stop(self):
        """거래 시스템 중지"""
        if not self.is_running:
            logger.warning("실행 중이 아닙니다")
            return

        logger.info("=== 거래 시스템 중지 ===")
        self.is_running = False

        # 중지 알림
        if self.telegram.enabled:
            await self.telegram.send_message(
                "⏸ 거래 시스템 중지\n자동 거래가 중지되었습니다."
            )

    async def shutdown(self):
        """시스템 종료"""
        logger.info("=== 시스템 종료 시작 ===")

        # 거래 중지
        if self.is_running:
            await self.stop()

        # 스크래퍼 종료
        if self.scraper:
            await self.scraper.close()

        # 텔레그램 봇 종료
        if self.telegram.enabled:
            await self.telegram.send_message(
                "👋 시스템 종료\n카피트레이딩 시스템을 종료합니다."
            )
            await self.telegram.stop_bot()

        logger.info("=== 시스템 종료 완료 ===")

    async def main_loop(self):
        """메인 실행 루프"""
        logger.info("메인 루프 시작")

        while self.is_running:
            try:
                # 1. 리더보드 스크래핑
                logger.info("리더보드 스크래핑 시작")
                traders = await self._scrape_with_retry()

                if traders:
                    logger.info(f"{len(traders)}명 트레이더 데이터 수집 완료")

                # 2. 신호 분석
                logger.info("신호 분석 시작")
                signals = self.signal_analyzer.analyze_signals()

                if signals:
                    logger.info(f"{len(signals)}개 신호 생성")

                    # 신호별로 처리
                    for signal in signals:
                        await self._process_signal(signal)

                # 3. 포지션 모니터링
                logger.info("포지션 모니터링")
                self.trade_executor.monitor_positions()

                # 4. 리스크 체크
                risk_summary = self.risk_manager.get_risk_summary()
                logger.info(
                    f"리스크 상태: "
                    f"포지션 {risk_summary.get('open_positions', 0)}개, "
                    f"일일 PnL: ${risk_summary.get('today_pnl', 0):.2f}"
                )

                # 5. 대기
                logger.info(f"{self.scraping_interval}초 대기 중...")
                await asyncio.sleep(self.scraping_interval)

            except KeyboardInterrupt:
                logger.info("사용자에 의해 중단됨")
                break
            except Exception as e:
                logger.error(f"메인 루프 오류: {e}")
                self.error_handler.handle_network_error(e)

                # 에러 알림
                if self.telegram.enabled:
                    await self.telegram.notify_error("메인 루프 오류", str(e))

                # 짧은 대기 후 재시도
                await asyncio.sleep(10)

        logger.info("메인 루프 종료")

    @get_error_handler().retry_on_error(max_retries=3, delay=10)
    async def _scrape_with_retry(self):
        """재시도 로직이 있는 스크래핑"""
        return await self.scraper.scrape_leaderboard()

    async def _process_signal(self, signal: dict):
        """신호 처리"""
        try:
            logger.info(f"신호 처리: {signal.get('symbol')} {signal.get('side')}")

            # 텔레그램 알림
            if self.telegram.enabled:
                await self.telegram.notify_signal(signal)

            # 거래 실행
            trade = self.trade_executor.execute_signal(signal)

            if trade:
                logger.info(f"거래 실행 성공: {trade.get('id')}")

                # 거래 오픈 알림
                if self.telegram.enabled:
                    await self.telegram.notify_trade_open(trade)
            else:
                logger.warning("거래 실행 실패")

        except Exception as e:
            logger.error(f"신호 처리 오류: {e}")
            if self.telegram.enabled:
                await self.telegram.notify_error("신호 처리 오류", str(e))

    async def send_daily_report(self):
        """일일 리포트 전송"""
        try:
            logger.info("일일 리포트 생성")

            performance = self.db.get_performance_history(days=1)
            if performance:
                today_perf = performance[0]

                # 텔레그램 알림
                if self.telegram.enabled:
                    await self.telegram.notify_daily_report(today_perf)

                logger.info("일일 리포트 전송 완료")

        except Exception as e:
            logger.error(f"일일 리포트 생성 실패: {e}")


# 전역 컨트롤러 인스턴스
_controller = None


def get_controller() -> TradingSystemController:
    """전역 컨트롤러 인스턴스 가져오기"""
    global _controller
    if _controller is None:
        _controller = TradingSystemController()
    return _controller


async def main():
    """메인 함수"""
    controller = TradingSystemController()

    # 시그널 핸들러 등록 (Ctrl+C 처리)
    def signal_handler(sig, frame):
        logger.info("종료 신호 수신")
        asyncio.create_task(controller.shutdown())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 초기화
        await controller.initialize()

        # 자동 시작 설정 확인
        auto_start = controller.config.get('system', 'auto_start', default=False)

        if auto_start:
            logger.info("자동 시작 설정 활성화")
            await controller.start()
        else:
            logger.info("수동 시작 대기 중 (API를 통해 시작하세요)")
            # 무한 대기
            while True:
                await asyncio.sleep(60)

    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"치명적 오류: {e}")
    finally:
        await controller.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
