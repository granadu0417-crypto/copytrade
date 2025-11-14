"""
바이낸스 카피트레이딩 시스템 메인 애플리케이션
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import setup_logger


def main():
    """메인 실행 함수"""
    logger = setup_logger()
    logger.info("바이낸스 카피트레이딩 시스템 시작")

    # TODO: 시스템 초기화 및 실행
    pass


if __name__ == "__main__":
    main()
