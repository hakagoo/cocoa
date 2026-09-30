"""모든 실험 스크립트가 동일한 포맷으로 로그를 남기게 하는 유틸.

표준 logging 모듈을 그대로 쓰되, 스크립트마다 포맷을 다르게 설정하는 실수를
막기 위해 이 모듈의 get_logger()만 거치도록 한다.
"""

from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """이름별로 통일된 포맷의 로거를 반환한다.

    같은 이름으로 여러 번 호출해도(예: 노트북 재실행) 핸들러가 중복으로
    쌓이지 않도록 이미 핸들러가 있으면 그대로 재사용한다.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(handler)
        logger.propagate = False
    return logger
