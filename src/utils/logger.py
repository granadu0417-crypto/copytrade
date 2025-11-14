"""
로깅 시스템 모듈
Loguru를 사용한 통합 로깅 관리
"""
from loguru import logger
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    log_file: str = "./logs/trading.log",
    level: str = "INFO",
    rotation: str = "500 MB",
    retention: str = "30 days",
    compression: str = "zip",
    format_string: Optional[str] = None
):
    """
    로거 설정

    Args:
        log_file: 로그 파일 경로
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        rotation: 로그 파일 회전 크기
        retention: 로그 파일 보관 기간
        compression: 압축 형식
        format_string: 커스텀 포맷 문자열

    Returns:
        logger: 설정된 로거 객체
    """
    # 기본 핸들러 제거
    logger.remove()

    # 기본 포맷
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

    # 콘솔 출력 핸들러
    logger.add(
        sys.stdout,
        format=format_string,
        level=level,
        colorize=True
    )

    # 로그 디렉토리 생성
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 파일 출력 핸들러
    logger.add(
        log_file,
        format=format_string,
        level=level,
        rotation=rotation,
        retention=retention,
        compression=compression,
        encoding="utf-8"
    )

    # 에러 로그 별도 저장
    error_log_file = log_path.parent / "error.log"
    logger.add(
        str(error_log_file),
        format=format_string,
        level="ERROR",
        rotation=rotation,
        retention=retention,
        compression=compression,
        encoding="utf-8"
    )

    logger.info("로거 초기화 완료")
    return logger


def get_logger():
    """로거 인스턴스 반환"""
    return logger


if __name__ == "__main__":
    # 테스트 코드
    test_logger = setup_logger(level="DEBUG")
    test_logger.debug("디버그 메시지")
    test_logger.info("정보 메시지")
    test_logger.warning("경고 메시지")
    test_logger.error("에러 메시지")
    test_logger.critical("치명적 에러 메시지")
