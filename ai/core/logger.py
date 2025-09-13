"""
이 모듈은 프로젝트 전반에서 사용될 로거를 설정합니다.
콘솔(stdout)과 파일에 로그를 동시에 출력하며, 일관된 형식의 로그 메시지를 제공합니다.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger():
    """
    프로젝트의 로깅 시스템을 설정하고, 전역 로거 인스턴스를 반환합니다.

    - 로그 레벨은 DEBUG로 설정하여 모든 레벨의 로그를 기록합니다.
    - 로그 형식은 [시간] [로그 레벨] [모듈명] [메시지] 형태로 통일합니다.
    - 로그는 콘솔과 `logs/app.log` 파일에 동시에 출력됩니다.
    - 파일 핸들러는 1MB 크기 제한과 5개의 백업 파일을 갖는 순환 방식을 사용합니다.

    Returns:
        logging.Logger: 설정이 완료된 로거 인스턴스
    """
    # Rule 4: "why" not just "what"
    # 'Angmini'라는 명명된 로거를 생성하여, 다른 라이브러리의 로거와 충돌하는 것을 방지하고,
    # 프로젝트의 모든 로그 출력을 중앙에서 관리할 수 있도록 합니다.
    logger = logging.getLogger("Angmini")
    logger.setLevel(logging.DEBUG)

    # 로거에 핸들러가 이미 설정되어 있는지 확인하여, 중복 추가를 방지합니다.
    # 이는 모듈이 여러 번 임포트될 때마다 핸들러가 계속 추가되는 것을 막아줍니다.
    if logger.hasHandlers():
        return logger

    # 로그 파일이 저장될 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 로그 형식 설정
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 설정 (순환 로그)
    # Rule 3: Root Cause Resolution
    # 단순 FileHandler 대신 RotatingFileHandler를 사용하여, 로그 파일이 무한정 커지는 것을
    # 근본적으로 방지합니다. 이는 장기 실행 시 발생할 수 있는 디스크 공간 문제를 예방합니다.
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# 프로젝트 전역에서 사용될 단일 로거 인스턴스
# 이 인스턴스를 임포트하여 어디서든 동일한 로깅 설정을 사용할 수 있습니다.
logger = setup_logger()
