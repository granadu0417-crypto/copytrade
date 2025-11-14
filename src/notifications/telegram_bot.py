"""
텔레그램 봇 알림 시스템
거래 신호, 포지션 변경, 에러 등을 텔레그램으로 알림
"""
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime

from src.utils.logger import get_logger
from src.utils.config_loader import get_config
from src.database.db_manager import DatabaseManager


logger = get_logger()


class TelegramNotifier:
    """텔레그램 알림 클래스"""

    def __init__(self, db_manager: DatabaseManager = None):
        """
        Args:
            db_manager: 데이터베이스 관리자
        """
        self.config = get_config()
        self.db = db_manager or DatabaseManager(self.config.get_database_path())

        # 텔레그램 설정 로드
        telegram_config = self.config.get('notifications', 'telegram', default={})

        self.enabled = telegram_config.get('enabled', False)
        self.bot_token = telegram_config.get('bot_token', '')
        self.chat_id = telegram_config.get('chat_id', '')

        # 알림 설정
        self.notify_on_signal = telegram_config.get('notify_on_signal', True)
        self.notify_on_trade = telegram_config.get('notify_on_trade', True)
        self.notify_on_close = telegram_config.get('notify_on_close', True)
        self.notify_on_error = telegram_config.get('notify_on_error', True)

        # Bot 인스턴스
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None

        if self.enabled and self.bot_token:
            self._initialize_bot()
        else:
            logger.warning("텔레그램 봇이 비활성화되어 있거나 토큰이 설정되지 않았습니다")

    def _initialize_bot(self):
        """텔레그램 봇 초기화"""
        try:
            self.bot = Bot(token=self.bot_token)
            self.application = Application.builder().token(self.bot_token).build()

            # 명령어 핸들러 등록
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("status", self.cmd_status))
            self.application.add_handler(CommandHandler("positions", self.cmd_positions))
            self.application.add_handler(CommandHandler("help", self.cmd_help))

            logger.info("텔레그램 봇 초기화 완료")

        except Exception as e:
            logger.error(f"텔레그램 봇 초기화 실패: {e}")
            self.enabled = False

    async def start_bot(self):
        """텔레그램 봇 시작"""
        if not self.enabled or not self.application:
            logger.warning("텔레그램 봇을 시작할 수 없습니다")
            return

        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("텔레그램 봇 실행 중")

        except Exception as e:
            logger.error(f"텔레그램 봇 시작 실패: {e}")

    async def stop_bot(self):
        """텔레그램 봇 중지"""
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("텔레그램 봇 중지됨")
            except Exception as e:
                logger.error(f"텔레그램 봇 중지 실패: {e}")

    async def send_message(self, message: str, parse_mode: str = 'Markdown'):
        """
        메시지 전송

        Args:
            message: 전송할 메시지
            parse_mode: 파싱 모드 (Markdown, HTML)
        """
        if not self.enabled or not self.bot or not self.chat_id:
            logger.debug(f"텔레그램 비활성화 상태 - 메시지 스킵: {message[:50]}...")
            return

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.debug(f"텔레그램 메시지 전송: {message[:50]}...")

        except Exception as e:
            logger.error(f"텔레그램 메시지 전송 실패: {e}")

    # ===== 알림 메서드 =====

    async def notify_signal(self, signal: Dict[str, Any]):
        """거래 신호 알림"""
        if not self.notify_on_signal:
            return

        symbol = signal.get('symbol', '-')
        side = signal.get('side', '-')
        consensus = signal.get('consensus_count', 0)
        price = signal.get('avg_entry_price', 0)

        message = f"""
🔔 *거래 신호 발생*

*심볼:* {symbol}
*방향:* {side}
*동의 수:* {consensus}명
*평균 진입가:* ${price:.2f}

신호가 감지되었습니다.
"""
        await self.send_message(message)

    async def notify_trade_open(self, trade: Dict[str, Any]):
        """거래 오픈 알림"""
        if not self.notify_on_trade:
            return

        symbol = trade.get('symbol', '-')
        side = trade.get('side', '-')
        entry_price = trade.get('entry_price', 0)
        quantity = trade.get('quantity', 0)
        leverage = trade.get('leverage', 1)

        emoji = "🟢" if side == "LONG" else "🔴"

        message = f"""
{emoji} *포지션 오픈*

*심볼:* {symbol}
*방향:* {side}
*진입가:* ${entry_price:.2f}
*수량:* {quantity}
*레버리지:* {leverage}x

거래가 실행되었습니다.
"""
        await self.send_message(message)

    async def notify_trade_close(self, trade: Dict[str, Any], pnl: float, reason: str):
        """거래 청산 알림"""
        if not self.notify_on_close:
            return

        symbol = trade.get('symbol', '-')
        side = trade.get('side', '-')
        entry_price = trade.get('entry_price', 0)
        exit_price = trade.get('exit_price', 0)
        pnl_pct = (pnl / (trade.get('quantity', 1) * entry_price)) * 100

        emoji = "✅" if pnl > 0 else "❌"
        pnl_text = f"+${pnl:.2f}" if pnl > 0 else f"${pnl:.2f}"

        message = f"""
{emoji} *포지션 청산*

*심볼:* {symbol}
*방향:* {side}
*진입가:* ${entry_price:.2f}
*청산가:* ${exit_price:.2f}
*PnL:* {pnl_text} ({pnl_pct:+.2f}%)
*사유:* {reason}

포지션이 청산되었습니다.
"""
        await self.send_message(message)

    async def notify_stop_loss(self, trade: Dict[str, Any]):
        """손절 알림"""
        symbol = trade.get('symbol', '-')
        side = trade.get('side', '-')

        message = f"""
🛑 *손절 트리거*

*심볼:* {symbol}
*방향:* {side}

손절가에 도달하여 포지션이 청산됩니다.
"""
        await self.send_message(message)

    async def notify_take_profit(self, trade: Dict[str, Any]):
        """익절 알림"""
        symbol = trade.get('symbol', '-')
        side = trade.get('side', '-')

        message = f"""
🎯 *익절 트리거*

*심볼:* {symbol}
*방향:* {side}

익절가에 도달하여 포지션이 청산됩니다.
"""
        await self.send_message(message)

    async def notify_error(self, error_type: str, error_msg: str):
        """에러 알림"""
        if not self.notify_on_error:
            return

        message = f"""
⚠️ *시스템 에러*

*유형:* {error_type}
*메시지:* {error_msg}

시스템 점검이 필요할 수 있습니다.
"""
        await self.send_message(message)

    async def notify_risk_alert(self, alert: Dict[str, Any]):
        """리스크 알림"""
        alert_type = alert.get('alert_type', '-')
        severity = alert.get('severity', 'WARNING')
        message_text = alert.get('message', '-')

        emoji = "🚨" if severity == "CRITICAL" else "⚠️"

        message = f"""
{emoji} *리스크 알림* ({severity})

*유형:* {alert_type}
*메시지:* {message_text}

즉시 확인이 필요합니다.
"""
        await self.send_message(message)

    async def notify_daily_report(self, performance: Dict[str, Any]):
        """일일 리포트 알림"""
        total_trades = performance.get('total_trades', 0)
        winning_trades = performance.get('winning_trades', 0)
        total_pnl = performance.get('total_pnl', 0)
        win_rate = performance.get('win_rate', 0)

        emoji = "📈" if total_pnl > 0 else "📉"
        pnl_text = f"+${total_pnl:.2f}" if total_pnl > 0 else f"${total_pnl:.2f}"

        message = f"""
{emoji} *일일 거래 리포트*

*총 거래:* {total_trades}건
*성공:* {winning_trades}건
*승률:* {win_rate:.1f}%
*총 PnL:* {pnl_text}

오늘 하루 수고하셨습니다!
"""
        await self.send_message(message)

    # ===== 명령어 핸들러 =====

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어"""
        message = """
🚀 바이낸스 카피트레이딩 봇에 오신 것을 환영합니다!

사용 가능한 명령어:
/status - 시스템 상태 확인
/positions - 현재 포지션 조회
/help - 도움말

알림이 활성화되었습니다.
"""
        await update.message.reply_text(message)

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """상태 명령어"""
        try:
            # 오픈 포지션 수
            open_trades = self.db.get_open_trades()
            open_count = len(open_trades)

            # 오늘 성과
            performance = self.db.get_performance_history(days=1)
            today_pnl = performance[0].get('total_pnl', 0) if performance else 0

            # 미해결 알림
            alerts = self.db.get_unresolved_alerts()

            message = f"""
📊 *시스템 상태*

*활성 포지션:* {open_count}개
*오늘 PnL:* ${today_pnl:.2f}
*미해결 알림:* {len(alerts)}개

시스템이 정상 작동 중입니다.
"""
            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"상태 조회 실패: {e}")

    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """포지션 명령어"""
        try:
            trades = self.db.get_open_trades()

            if not trades:
                await update.message.reply_text("현재 오픈된 포지션이 없습니다.")
                return

            message = "📋 *현재 포지션*\n\n"

            for trade in trades[:10]:  # 최대 10개
                symbol = trade.get('symbol', '-')
                side = trade.get('side', '-')
                entry = trade.get('entry_price', 0)

                message += f"• {symbol} {side} @ ${entry:.2f}\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"포지션 조회 실패: {e}")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """도움말 명령어"""
        message = """
📖 *명령어 도움말*

/start - 봇 시작
/status - 시스템 상태 확인
/positions - 현재 포지션 조회
/help - 이 도움말 표시

알림은 자동으로 전송됩니다:
• 거래 신호 발생
• 포지션 오픈/청산
• 손절/익절
• 시스템 에러
• 일일 리포트
"""
        await update.message.reply_text(message, parse_mode='Markdown')


# 전역 인스턴스
_telegram_notifier = None


def get_telegram_notifier() -> TelegramNotifier:
    """전역 텔레그램 알리미 인스턴스 가져오기"""
    global _telegram_notifier
    if _telegram_notifier is None:
        _telegram_notifier = TelegramNotifier()
    return _telegram_notifier


if __name__ == "__main__":
    # 테스트 코드
    async def test():
        notifier = TelegramNotifier()

        if notifier.enabled:
            # 테스트 메시지 전송
            await notifier.send_message("🧪 텔레그램 봇 테스트 메시지")

            # 테스트 신호 알림
            test_signal = {
                'symbol': 'BTC/USDT',
                'side': 'LONG',
                'consensus_count': 5,
                'avg_entry_price': 50000
            }
            await notifier.notify_signal(test_signal)

        else:
            print("텔레그램 봇이 비활성화되어 있습니다")

    asyncio.run(test())
