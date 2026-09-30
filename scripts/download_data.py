"""Open Bandit Dataset을 공식 링크에서 내려받는 스크립트.

이 스크립트는 고정된 단일 공개 연구 데이터셋 아카이브를 정해진 하나의
URL에서 그대로 받아오는 것으로, 여러 페이지를 순회하며 콘텐츠를 수집하는
웹 크롤러가 아니다(CLAUDE.md §2 범위 제외 항목과는 다르다).

Criteo Attribution Dataset은 공식 다운로드 링크(go.criteo.net)가
2026-09-30 확인 시점에 404를 반환해 자동화하지 않는다. docs/DATA.md의
수동 절차를 따른다.

사용:
    python scripts/download_data.py --dataset open_bandit
    python scripts/download_data.py --dataset criteo   # 수동 절차 안내만 출력
    python scripts/download_data.py --dataset all
"""

from __future__ import annotations

import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path

from cocoa.utils.logging import get_logger

logger = get_logger(__name__)

OPEN_BANDIT_DATASET_URL = "https://research.zozo.com/data_release/open_bandit_dataset.zip"
# 2026-09-30 curl -I로 확인한 Content-Length. 배포처가 파일을 교체하면
# 달라질 수 있으므로 실패 조건이 아니라 경고 용도로만 쓴다.
OPEN_BANDIT_DATASET_EXPECTED_SIZE_BYTES = 412_931_917

CRITEO_ATTRIBUTION_PAGE_URL = (
    "https://ailab.criteo.com/criteo-attribution-modeling-bidding-dataset/"
)


def download_open_bandit_dataset(dest_dir: Path, force: bool = False) -> Path:
    """Open Bandit Dataset 공식 zip을 받아 dest_dir 아래에 압축을 푼다.

    출처: https://research.zozo.com/data.html (등록·약관 동의 불필요, 직접
    다운로드 링크). 사용 시 논문(Saito et al., arXiv:2008.07146) 인용을
    요청하고 있다.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    already_downloaded = any(dest_dir.iterdir())
    if already_downloaded and not force:
        logger.info("%s 에 이미 파일이 있어 건너뜀 (--force로 재다운로드)", dest_dir)
        return dest_dir

    zip_path = dest_dir / "open_bandit_dataset.zip"
    logger.info("다운로드 시작: %s", OPEN_BANDIT_DATASET_URL)
    urllib.request.urlretrieve(OPEN_BANDIT_DATASET_URL, zip_path)

    actual_size = zip_path.stat().st_size
    if actual_size != OPEN_BANDIT_DATASET_EXPECTED_SIZE_BYTES:
        logger.warning(
            "다운로드 파일 크기가 확인 시점(2026-09-30, %d bytes)과 다르다: %d bytes. "
            "배포처가 파일을 갱신했을 수 있으니 내용을 직접 확인할 것.",
            OPEN_BANDIT_DATASET_EXPECTED_SIZE_BYTES,
            actual_size,
        )

    logger.info("압축 해제 중: %s", zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    zip_path.unlink()

    # 이 zip은 최상위에 "open_bandit_dataset/" 폴더 하나만 담고 있고(2026-09-30
    # 확인), 그 안에 {bts,random}/{all,men,women}/*.csv가 있다. obp가 기대하는
    # <data_path>/{behavior_policy}/{campaign}/{campaign}.csv 형태로 바로 쓸 수
    # 있도록 안쪽 내용물을 dest_dir로 한 단계 끌어올린다.
    top_level_entries = list(dest_dir.iterdir())
    if len(top_level_entries) == 1 and top_level_entries[0].is_dir():
        wrapper_dir = top_level_entries[0]
        for entry in wrapper_dir.iterdir():
            shutil.move(str(entry), str(dest_dir / entry.name))
        wrapper_dir.rmdir()

    logger.info(
        "압축 해제 완료: %s. 최상위 항목: %s",
        dest_dir,
        sorted(p.name for p in dest_dir.iterdir()),
    )
    logger.info(
        "실제 파일로 확인된 구조(2026-09-30): <data_path>/{bts,random}/{all,men,women}/"
        "{campaign}.csv + item_context.csv. obp.dataset.OpenBanditDataset(data_path=...)"
        "에는 이 dest_dir을 그대로 넘기면 된다."
    )
    logger.warning(
        "CLAUDE.md §2는 position을 0/1/2로 가정하지만, 실제 CSV의 position 값은 "
        "1/2/3(좌/중/우)이다 — 직접 파일을 열어 확인한 결과(2026-09-30). "
        "action_context.py 구현 시(T1.4) 이 차이를 반드시 반영할 것."
    )
    return dest_dir


def print_criteo_manual_instructions() -> None:
    """Criteo Attribution Dataset은 자동 다운로드하지 않고 수동 절차만 안내한다."""
    logger.info(
        "Criteo Attribution Dataset은 자동 다운로드하지 않는다. "
        "공식 페이지(%s)에서 현재 유효한 다운로드 링크를 직접 확인해 받고, "
        "data/raw/criteo_attribution/ 에 압축을 풀 것. 자세한 절차와 주의사항은 "
        "docs/DATA.md를 참고할 것.",
        CRITEO_ATTRIBUTION_PAGE_URL,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", choices=["open_bandit", "criteo", "all"], default="all"
    )
    parser.add_argument("--dest", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--force", action="store_true", help="이미 받은 파일이 있어도 다시 받는다"
    )
    args = parser.parse_args()

    if args.dataset in ("open_bandit", "all"):
        download_open_bandit_dataset(
            args.dest / "open_bandit_dataset", force=args.force
        )
    if args.dataset in ("criteo", "all"):
        print_criteo_manual_instructions()


if __name__ == "__main__":
    main()
