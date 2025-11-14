"""
바이낸스 카피트레이딩 시스템 메인 애플리케이션
"""
import os
import sys
import asyncio
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import setup_logger
from src.main_controller import TradingSystemController


def main():
    """메인 실행 함수"""
    logger = setup_logger()
    logger.info("=" * 50)
    logger.info("바이낸스 카피트레이딩 시스템 시작")
    logger.info("=" * 50)

    # 메인 컨트롤러 실행
    controller = TradingSystemController()

    try:
        asyncio.run(controller.initialize())

        # 시스템 실행 (API 서버 또는 메인 루프)
        mode = input("\n실행 모드를 선택하세요:\n1. API 서버 (웹 대시보드)\n2. 자동 거래 (메인 루프)\n선택 (1/2): ").strip()

        if mode == '1':
            logger.info("API 서버 모드로 실행합니다")
            from src.api.server import app
            import uvicorn
            from src.utils.config_loader import get_config

            config = get_config()
            webserver_config = config.get('webserver', default={})
            host = webserver_config.get('host', '0.0.0.0')
            port = webserver_config.get('port', 8000)

            logger.info(f"웹서버 시작: http://{host}:{port}")
            logger.info("웹 대시보드에서 시스템을 제어할 수 있습니다")

            uvicorn.run(app, host=host, port=port)

        elif mode == '2':
            logger.info("자동 거래 모드로 실행합니다")
            asyncio.run(controller.start())
        else:
            logger.error("잘못된 선택입니다")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단됨")
        asyncio.run(controller.shutdown())
    except Exception as e:
        logger.error(f"치명적 오류: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
