"""
바이낸스 리더보드 웹 스크래핑 모듈
Playwright를 사용하여 상위 트레이더 정보 및 포지션 수집
"""
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import re

from src.utils.logger import get_logger
from src.utils.config_loader import get_config
from src.database.db_manager import DatabaseManager


logger = get_logger()


class LeaderboardScraper:
    """바이낸스 리더보드 스크래핑 클래스"""

    def __init__(self, db_manager: DatabaseManager = None):
        """
        Args:
            db_manager: 데이터베이스 관리자 인스턴스
        """
        self.config = get_config()
        self.db = db_manager or DatabaseManager(self.config.get_database_path())

        # 스크래핑 설정
        scraping_config = self.config.get('scraping', default={})
        self.leaderboard_url = scraping_config.get(
            'leaderboard_url',
            'https://www.binance.com/en/futures-activity/leaderboard'
        )
        self.timeout = scraping_config.get('timeout', 30) * 1000  # 밀리초 변환
        self.headless = scraping_config.get('headless', True)
        self.user_agent = scraping_config.get('user_agent')

        # 전략 설정
        strategy_config = self.config.get_strategy_config()
        self.tracked_traders_count = strategy_config.get('tracked_traders', 15)

        # Playwright 객체
        self.playwright = None
        self.browser: Optional[Browser] = None

    async def initialize(self):
        """브라우저 초기화"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless
            )
            logger.info("브라우저 초기화 완료")
        except Exception as e:
            logger.error(f"브라우저 초기화 실패: {e}")
            raise

    async def close(self):
        """브라우저 종료"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("브라우저 종료 완료")

    async def scrape_leaderboard(self) -> List[Dict[str, Any]]:
        """
        리더보드에서 상위 트레이더 정보 스크래핑

        Returns:
            트레이더 정보 리스트
        """
        if not self.browser:
            await self.initialize()

        traders = []

        try:
            page = await self.browser.new_page(
                user_agent=self.user_agent if self.user_agent else None
            )

            # 리더보드 페이지 접속
            logger.info(f"리더보드 페이지 접속: {self.leaderboard_url}")
            await page.goto(self.leaderboard_url, timeout=self.timeout)

            # 페이지 로딩 대기
            await page.wait_for_load_state('networkidle', timeout=self.timeout)
            await asyncio.sleep(2)  # 동적 콘텐츠 로딩 대기

            # 페이지 HTML 가져오기
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # 트레이더 정보 파싱
            # 주의: 실제 바이낸스 페이지 구조에 맞게 셀렉터 수정 필요
            traders_data = await self._parse_traders(page, soup)

            logger.info(f"수집된 트레이더 수: {len(traders_data)}")

            # 각 트레이더의 상세 정보 및 포지션 수집
            for i, trader_data in enumerate(traders_data[:self.tracked_traders_count]):
                if i >= self.tracked_traders_count:
                    break

                # 트레이더 상세 정보 수집
                trader_info = await self._scrape_trader_details(
                    page,
                    trader_data
                )

                if trader_info:
                    traders.append(trader_info)
                    # 데이터베이스에 저장
                    self.db.add_trader(trader_info)

                # 요청 간격 (Rate Limit 방지)
                await asyncio.sleep(1)

            await page.close()

        except Exception as e:
            logger.error(f"리더보드 스크래핑 실패: {e}")
            raise

        return traders

    async def _parse_traders(self, page: Page, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        리더보드에서 트레이더 정보 파싱

        Note: 실제 바이낸스 페이지 구조에 맞게 수정 필요
        """
        traders = []

        # TODO: 실제 바이낸스 리더보드 HTML 구조 분석 후 셀렉터 수정
        # 예시 구조 (실제와 다를 수 있음)
        trader_elements = soup.select('.trader-row')  # 예시 셀렉터

        for element in trader_elements:
            try:
                # 각 요소를 먼저 찾아서 변수에 저장
                nickname_elem = element.select_one('.nickname')
                roi_7d_elem = element.select_one('.roi-7d')
                roi_30d_elem = element.select_one('.roi-30d')
                pnl_elem = element.select_one('.pnl')
                win_rate_elem = element.select_one('.win-rate')
                followers_elem = element.select_one('.followers')

                trader_data = {
                    'binance_uid': element.get('data-uid', ''),
                    'nickname': nickname_elem.text.strip() if nickname_elem else '',
                    'roi_7d': self._parse_percentage(roi_7d_elem.text) if roi_7d_elem else 0.0,
                    'roi_30d': self._parse_percentage(roi_30d_elem.text) if roi_30d_elem else 0.0,
                    'pnl': self._parse_number(pnl_elem.text) if pnl_elem else 0.0,
                    'win_rate': self._parse_percentage(win_rate_elem.text) if win_rate_elem else 0.0,
                    'followers': self._parse_number(followers_elem.text) if followers_elem else 0,
                }
                traders.append(trader_data)
            except Exception as e:
                logger.warning(f"트레이더 파싱 오류: {e}")
                continue

        return traders

    async def _scrape_trader_details(
        self,
        page: Page,
        trader_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        개별 트레이더 상세 정보 및 포지션 수집

        Args:
            page: Playwright 페이지 객체
            trader_data: 기본 트레이더 정보

        Returns:
            상세 트레이더 정보
        """
        try:
            # 트레이더 상세 페이지 접속
            trader_uid = trader_data.get('binance_uid')
            if not trader_uid:
                return None

            detail_url = f"{self.leaderboard_url}/{trader_uid}"
            await page.goto(detail_url, timeout=self.timeout)
            await page.wait_for_load_state('networkidle', timeout=self.timeout)
            await asyncio.sleep(1)

            # 포지션 정보 수집
            positions = await self._scrape_positions(page, trader_data)

            # 트레이더 정보에 포지션 추가
            trader_info = trader_data.copy()
            trader_info['positions'] = positions
            trader_info['total_trades'] = len(positions)

            logger.info(
                f"트레이더 {trader_info.get('nickname', 'Unknown')} "
                f"포지션 수: {len(positions)}"
            )

            return trader_info

        except Exception as e:
            logger.error(f"트레이더 상세 정보 수집 실패 ({trader_data.get('nickname')}): {e}")
            return None

    async def _scrape_positions(
        self,
        page: Page,
        trader_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        트레이더의 현재 포지션 수집

        Args:
            page: Playwright 페이지 객체
            trader_data: 트레이더 기본 정보

        Returns:
            포지션 정보 리스트
        """
        positions = []

        try:
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # TODO: 실제 포지션 테이블 구조에 맞게 셀렉터 수정
            position_elements = soup.select('.position-row')  # 예시 셀렉터

            for element in position_elements:
                try:
                    # 각 요소를 먼저 찾아서 변수에 저장
                    symbol_elem = element.select_one('.symbol')
                    side_elem = element.select_one('.side')
                    entry_price_elem = element.select_one('.entry-price')
                    current_price_elem = element.select_one('.current-price')
                    quantity_elem = element.select_one('.quantity')
                    leverage_elem = element.select_one('.leverage')
                    pnl_elem = element.select_one('.pnl')
                    pnl_pct_elem = element.select_one('.pnl-pct')

                    position_data = {
                        'trader_id': None,  # DB 저장 후 업데이트
                        'symbol': symbol_elem.text.strip() if symbol_elem else '',
                        'side': side_elem.text.strip() if side_elem else '',
                        'entry_price': self._parse_number(entry_price_elem.text) if entry_price_elem else 0.0,
                        'current_price': self._parse_number(current_price_elem.text) if current_price_elem else 0.0,
                        'quantity': self._parse_number(quantity_elem.text) if quantity_elem else 0.0,
                        'leverage': int(self._parse_number(leverage_elem.text) if leverage_elem else 1),
                        'pnl': self._parse_number(pnl_elem.text) if pnl_elem else 0.0,
                        'pnl_percentage': self._parse_percentage(pnl_pct_elem.text) if pnl_pct_elem else 0.0,
                        'detected_at': datetime.now(),
                    }

                    # LONG/SHORT 정규화
                    if 'long' in position_data['side'].lower():
                        position_data['side'] = 'LONG'
                    elif 'short' in position_data['side'].lower():
                        position_data['side'] = 'SHORT'

                    positions.append(position_data)

                except Exception as e:
                    logger.warning(f"포지션 파싱 오류: {e}")
                    continue

        except Exception as e:
            logger.error(f"포지션 수집 실패: {e}")

        return positions

    @staticmethod
    def _parse_number(text: Optional[str]) -> Optional[float]:
        """문자열에서 숫자 추출"""
        if not text:
            return None

        try:
            # 쉼표, % 등 제거하고 숫자만 추출
            cleaned = re.sub(r'[^\d.-]', '', text.strip())
            return float(cleaned) if cleaned else None
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _parse_percentage(text: Optional[str]) -> Optional[float]:
        """퍼센티지 문자열을 float으로 변환"""
        if not text:
            return None

        try:
            # %와 공백 제거
            cleaned = text.strip().replace('%', '')
            return float(cleaned) if cleaned else None
        except (ValueError, AttributeError):
            return None

    async def save_positions_to_db(self, trader_uid: str, positions: List[Dict[str, Any]]):
        """포지션을 데이터베이스에 저장"""
        try:
            # 트레이더 ID 조회
            trader = self.db.get_trader_by_uid(trader_uid)
            if not trader:
                logger.warning(f"트레이더를 찾을 수 없음: {trader_uid}")
                return

            trader_id = trader['id']

            # 포지션 저장
            for position in positions:
                position['trader_id'] = trader_id
                self.db.add_position(position)

            logger.info(f"{len(positions)}개 포지션 저장 완료")

        except Exception as e:
            logger.error(f"포지션 저장 실패: {e}")


async def main():
    """테스트 코드"""
    scraper = LeaderboardScraper()
    try:
        await scraper.initialize()
        traders = await scraper.scrape_leaderboard()
        logger.info(f"총 {len(traders)}명의 트레이더 정보 수집 완료")

        for trader in traders:
            logger.info(
                f"트레이더: {trader.get('nickname', 'Unknown')} | "
                f"ROI 7d: {trader.get('roi_7d')}% | "
                f"포지션 수: {len(trader.get('positions', []))}"
            )

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
