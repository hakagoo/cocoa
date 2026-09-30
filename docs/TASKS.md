# COCOA 태스크 목록

CLAUDE.md §10 로드맵을 실행 단위로 분해한 목록이다. Phase 순서는 의존성을
반영한다(뒤 Phase는 앞 Phase 산출물을 입력으로 받음). 각 태스크는 완료 기준과
필요 테스트를 함께 적는다.

## Phase 0 — 프로젝트 셋업

- [x] **T0.1** `pyproject.toml` 의존성 버전 확정. `obp` 설치 가능한 Python 버전을
      실제로 설치해 확인. 결과: obp 0.5.x는 `torch==1.12.0`에 하드 고정되어 있어
      Python 3.11+에서는 설치 불가(휠 없음) → 버전 미지정 시 resolver가 자동으로
      `obp==0.4.1`을 선택함. 0.4.1은 하한만 있는 느슨한 의존성이라 numpy 2.x /
      pandas 3.x / scikit-learn 1.9 / torch 2.14와 함께 Python 3.11·3.13·3.14에서
      설치 및 기능 스모크테스트(SyntheticBanditDataset, Random 정책, IPS/SNIPS/DR,
      RegressionModel) 모두 통과. 3.9/3.10은 네트워크 제약으로 이번 검증 환경에서
      인터프리터를 새로 받을 수 없어 미검증(필요 시 별도 확인).
      → `requires-python = ">=3.11"`, `obp>=0.4.1,<0.5`로 고정하고
      `uv lock`으로 `uv.lock` 생성, `uv sync`로 `.venv` 설치까지 확인함.
- [x] **T0.2** 저장소 디렉토리 스캐폴드 (`src/cocoa/*`, `configs/`, `data/`,
      `scripts/`, `notebooks/`, `results/`, `tests/`, `docs/`)
- [x] **T0.3** `utils/seed.py`, `utils/logging.py`, `utils/config.py` 기본 유틸 구현.
      `seed.py`는 `set_seed()`(random/numpy/torch 전역 고정)와 `get_rng()`(독립
      Generator, 다중 시드 실험용)를 제공. `logging.py`는 `get_logger()`로 포맷
      통일. `config.py`는 `load_yaml()`, `get_git_commit_hash()`,
      `save_run_metadata()`(설정+시드+git hash를 결과 옆 JSON으로 저장)를 제공.
      `tests/test_utils.py` 8개 테스트 모두 통과.
- [ ] **T0.4** `data/raw/`에 Open Bandit Dataset, Criteo 원본을 받는 절차 정리
      (`scripts/download_data.py` 또는 README에 수동 절차 기록)

의존성: 없음 (최초 단계)

## Phase 1 — 데이터 로더 & 시간 분할

- [ ] **T1.1** Open Bandit Dataset 로더 (`data/open_bandit_loader.py`).
      `obp` 패키지로 로드, `random`/`bts` behavior policy 모두 지원
- [ ] **T1.2** Criteo Attribution 로더 (`data/criteo_loader.py`).
      **실제 다운로드한 CSV를 열어 컬럼명 확인 후 구현** (추측 금지, CLAUDE.md §3)
- [ ] **T1.3** 시간 기준 분할 (`data/time_split.py`): train/eval 경계 함수 +
      "eval 기간 데이터가 학습에 안 섞였는지" 검증 유틸
- [ ] **T1.4** 행동·맥락 정의 (`data/action_context.py`): (제휴 상품, position 0/1/2)
      행동 스키마, 맥락 벡터 구성
- [ ] **T1.5 (테스트)** `tests/test_time_split.py` — 경계값, 누수 여부

의존성: T0.3 (설정/로깅 유틸)
완료 기준: Open Bandit/Criteo 각각을 로드해 학습/평가 기간으로 나눈 DataFrame을
반환하는 함수가 동작하고, 분할 경계 테스트 통과

## Phase 2 — `reward_assumptions.yaml` 스키마 & 반합성 보상

- [ ] **T2.1** `configs/reward_assumptions.yaml`의 실제 카테고리/가격/수수료율/
      취소율 값 조사해 채움 (비개발자 팀원 협업 — 스캐폴드는 placeholder만 있음)
- [ ] **T2.2** `reward/assumptions.py`: yaml 로드 + 스키마 검증(누락 카테고리,
      범위(0~1) 벗어난 비율 등 즉시 실패)
- [ ] **T2.3** `reward/semisynthetic.py`: 실현 보상 `r` 계산 함수
- [ ] **T2.4** `reward/semisynthetic.py`: 기대 보상 `E[r|x,a]` 계산 함수
- [ ] **T2.5 (테스트)** `tests/test_reward.py`

의존성: T1.4(행동 정의), T2.1(가정값)
완료 기준: 클릭/전환/취소 조합별 보상이 CLAUDE.md §4 공식과 일치함을 테스트로 확인

## Phase 3 — 지연 전환 모델 (Chapelle 2014)

- [ ] **T3.1** Criteo 데이터로 `p(x)` (전환확률) 분류기 학습
- [ ] **T3.2** `lam(x)` (전환 속도) 추정 — 생존분석/해저드 모델
- [ ] **T3.3** `reward/delayed_conversion.py`: soft label 공식 구현
      `P(conv=1|미확정,x,e) = p(x)*exp(-lam(x)*e) / (1 - p(x) + p(x)*exp(-lam(x)*e))`
- [ ] **T3.4** attribution window 종료/전환 확정 시 soft label → 실값 교정 로직
- [ ] **T3.5 (테스트)** `tests/test_delayed_conversion.py` — e→0, e→∞ 극한값 검증

의존성: T1.2(Criteo 로더)
완료 기준: 학습된 `p(x)`, `lam(x)`가 `data/processed/`에 저장되고, soft label
함수가 극한에서 이론값에 수렴함을 테스트로 확인

## Phase 4 — 합성 환경 (지연·취소 포함)

- [ ] **T4.1** `envs/synthetic_env.py`: `obp.dataset.SyntheticBanditDataset` 래핑,
      참 보상함수 노출
- [ ] **T4.2** `envs/delay_cancel_wrapper.py`: Phase 3의 지연 분포를 이용해
      전환 시각 샘플링 + 취소 주입, 클릭/확정 이벤트 스트림 생성
- [ ] **T4.3 (테스트)** `tests/test_synthetic_env.py`

의존성: T2.3~T2.4(보상 계산), T3.3(지연 분포)
완료 기준: 환경에서 시뮬레이션한 에피소드가 참 보상함수와 관측 보상 모두를
반환하고, regret 계산에 바로 쓸 수 있음

## Phase 5 — 베이스라인 정책

- [ ] **T5.1** `policies/base.py`: `Policy` Protocol, `Action`/`Feedback` 데이터클래스
- [ ] **T5.2** `policies/random_policy.py`, `logging_policy.py`
- [ ] **T5.3** `policies/greedy.py`
- [ ] **T5.4** `policies/epsilon_greedy.py`
- [ ] **T5.5** `policies/linucb.py` (Li et al. 2010)
- [ ] **T5.6 (테스트)** `tests/test_policies.py` (baseline 부분) — propensity 범위,
      `update()` 후 상태 변화 sanity check

의존성: T1.4(행동 정의), T2.4(기대 보상 — greedy 계열이 사용)
완료 기준: 5개 정책이 동일 인터페이스로 합성 환경/오프라인 로그 양쪽에서 동작

## Phase 6 — Neural-Linear TS & 제안 방법

- [ ] **T6.1** `policies/neural_linear_ts.py`: 기본 Neural-Linear TS
      (확정된 전환만 학습에 반영, Riquelme et al. 2018)
- [ ] **T6.2** `policies/delay_cancel_ts.py`: 제안 방법. soft label(T3.3)을
      1차 갱신에 사용하고 확정 시 교정, 취소 확률 보정 반영
- [ ] **T6.3** `policies/ablation.py`: 제거 실험 2종
      (지연 보정만 제거 / 취소 보정만 제거) — `delay_cancel_ts.py` 상속·플래그 분기
- [ ] **T6.4** 사후 샘플링 몬테카를로 기반 propensity 근사 구현
- [ ] **T6.5 (테스트)** `tests/test_policies.py` (TS 계열 부분)

의존성: T3.3(soft label), T5.1(Policy 인터페이스)
완료 기준: 6개 정책 변형(기본 TS, 제안, 제거실험 2종 포함) 모두 propensity를
반환하며 클릭/확정 이벤트를 구분해 갱신됨

## Phase 7 — 평가: 후회, OPE, 신뢰구간

- [ ] **T7.1** `evaluation/regret.py`: 합성 환경 누적 후회, H1/H2 판정
- [ ] **T7.2** `evaluation/ope_estimators.py`: IPS/SNIPS/DR (obp 추정량 래핑 또는 직접 구현)
- [ ] **T7.3** random 로그로 bts 정책 가치 추정 → 실제 기록값과 오차 비교
      (추정량 정확도 검증, H3 전 단계)
- [ ] **T7.4** 가장 정확한 추정량으로 제안 정책 평가 (H3 판정)
- [ ] **T7.5** `evaluation/confidence_interval.py`: 부트스트랩 CI,
      신뢰구간 하한(95%) > 0일 때만 "개선"으로 판정하는 규칙 강제
- [ ] **T7.6** 시드 10개 이상 실행 파이프라인 (`scripts/train.py` + `scripts/evaluate.py`)
- [ ] **T7.7 (테스트)** `tests/test_ope_estimators.py` — 정답을 아는 장난감 예제로 검증

의존성: Phase 4(합성 환경), Phase 5·6(정책)
완료 기준: H1~H3 판정 결과가 상대 지표(로깅 정책 대비 개선률)로 재현 가능하게 산출

## Phase 8 — 민감도 분석 & 결과 산출물

- [ ] **T8.1** `evaluation/sensitivity.py`: `reward_assumptions.yaml`
      `sensitivity_grid` 순회, 정책 순위 Kendall tau 계산 (H4)
- [ ] **T8.2** `scripts/run_sensitivity.py`
- [ ] **T8.3** `scripts/report.py`: 표/그림 생성 (상대 지표만, 절대 금액 금지)
- [ ] **T8.4** `results/`에 설정+시드+git commit hash를 포함한 최종 결과 정리

의존성: Phase 7 전체
완료 기준: H1~H4 판정과 근거 표/그림이 `results/`에 재현 가능한 형태로 존재

## 교차 우려사항 (전 Phase 공통)

- 모든 PR/커밋에서 평가 셋 누수 가능성이 있는 변경은 먼저 알린다 (CLAUDE.md §9)
- 핵심 로직 변경 시 해당 테스트를 함께 갱신한다
- 새 라이브러리 추가 전 이유를 설명하고 확인받는다 (CLAUDE.md §8)
- 범위 밖 기능(MDP/RL, 광고 채널, LLM 문구 생성 등)이 필요해 보이면 구현하지
  않고 먼저 질문한다 (CLAUDE.md §2)
