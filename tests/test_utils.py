"""utils/seed.py, utils/logging.py, utils/config.py에 대한 단위 테스트."""

from __future__ import annotations

import json
import logging

import numpy as np
import torch

from cocoa.utils.config import get_git_commit_hash, load_yaml, save_run_metadata
from cocoa.utils.logging import get_logger
from cocoa.utils.seed import get_rng, set_seed


def test_set_seed_makes_numpy_reproducible() -> None:
    set_seed(42)
    first = np.random.rand(5)
    set_seed(42)
    second = np.random.rand(5)
    assert np.array_equal(first, second)


def test_set_seed_makes_torch_reproducible() -> None:
    set_seed(42)
    first = torch.rand(5)
    set_seed(42)
    second = torch.rand(5)
    assert torch.equal(first, second)


def test_get_rng_independent_of_global_state() -> None:
    set_seed(0)
    rng_a = get_rng(123)
    rng_b = get_rng(123)
    assert np.array_equal(rng_a.random(5), rng_b.random(5))


def test_get_logger_reuses_handlers() -> None:
    logger_first = get_logger("cocoa.test_logger")
    logger_second = get_logger("cocoa.test_logger")
    assert logger_first is logger_second
    assert len(logger_first.handlers) == 1
    assert logger_first.level == logging.INFO


def test_load_yaml_roundtrip(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("seed: 0\nname: test\n", encoding="utf-8")

    config = load_yaml(config_path)

    assert config == {"seed": 0, "name": "test"}


def test_load_yaml_rejects_empty_file(tmp_path) -> None:
    config_path = tmp_path / "empty.yaml"
    config_path.write_text("", encoding="utf-8")

    try:
        load_yaml(config_path)
        assert False, "빈 yaml 파일은 ValueError를 내야 한다"
    except ValueError:
        pass


def test_get_git_commit_hash_returns_nonempty_string() -> None:
    commit_hash = get_git_commit_hash()
    assert isinstance(commit_hash, str)
    assert commit_hash != ""


def test_save_run_metadata_writes_config_seed_and_hash(tmp_path) -> None:
    result_path = tmp_path / "exp1_seed0.meta.json"

    save_run_metadata(result_path, config={"policy": "random"}, seed=0)

    saved = json.loads(result_path.read_text(encoding="utf-8"))
    assert saved["config"] == {"policy": "random"}
    assert saved["seed"] == 0
    assert "git_commit_hash" in saved
