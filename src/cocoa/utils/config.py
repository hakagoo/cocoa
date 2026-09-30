"""yaml 설정 로드, 그리고 결과 파일에 설정·시드·git commit hash를 함께 남기는 유틸.

CLAUDE.md §9: "모든 실험은 설정 파일 + 시드로 재현 가능해야 한다", "결과 파일에는
실험 설정, 시드, git 커밋 해시를 함께 기록한다." 두 규칙을 강제하기 위한 모듈이다.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    """yaml 설정 파일을 dict로 읽는다. 프로젝트 내 모든 yaml 로드는 이 함수를 거친다."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if config is None:
        raise ValueError(f"설정 파일이 비어 있다: {path}")
    return config


def get_git_commit_hash(cwd: str | Path | None = None) -> str:
    """현재 git commit hash를 반환한다.

    커밋되지 않은 변경이 있으면 "-dirty"를 붙여, 결과가 정확히 어떤 커밋
    상태에서 나왔는지 구분할 수 있게 한다. git 저장소가 아니거나 git이 없으면
    "unknown"을 반환한다(테스트 환경 등에서 실패하지 않도록).
    """
    try:
        commit_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        is_dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
        return f"{commit_hash}-dirty" if is_dirty else commit_hash
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


@dataclass
class RunMetadata:
    """실험 결과 파일 옆에 함께 저장할 메타데이터."""

    config: dict[str, Any]
    seed: int
    git_commit_hash: str = field(default_factory=get_git_commit_hash)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config,
            "seed": self.seed,
            "git_commit_hash": self.git_commit_hash,
        }


def save_run_metadata(path: str | Path, config: dict[str, Any], seed: int) -> None:
    """결과 파일과 짝이 되는 메타데이터 JSON을 저장한다.

    예: results/exp1_seed0.csv 를 만들었다면
        results/exp1_seed0.meta.json 을 이 함수로 함께 남긴다.
    """
    metadata = RunMetadata(config=config, seed=seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(metadata.to_dict(), f, ensure_ascii=False, indent=2)
