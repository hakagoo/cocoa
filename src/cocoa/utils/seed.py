"""모든 난수 초기화의 단일 진입점.

CLAUDE.md §9: "난수는 utils의 시드 함수로만 초기화한다." 정책·환경·평가 코드에서
np.random.seed()나 torch.manual_seed()를 직접 호출하지 말고 이 모듈만 사용한다.
"""

from __future__ import annotations

import random

import numpy as np
import torch


def set_seed(seed: int) -> None:
    """random/numpy/torch의 전역 난수 상태를 모두 동일한 시드로 고정한다."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_rng(seed: int) -> np.random.Generator:
    """전역 상태를 건드리지 않는 독립 numpy Generator를 만든다.

    여러 시드를 동시에 돌리는 실험(CLAUDE.md §6-7: 시드 10개 이상)에서
    정책·환경 인스턴스마다 서로 간섭하지 않는 난수 스트림이 필요할 때 쓴다.
    """
    return np.random.default_rng(seed)
