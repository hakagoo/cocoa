# COCOA 아키텍처 설계

CLAUDE.md(연구 범위·데이터·보상 정의·정책·평가 원칙)를 코드 구조로 옮긴 문서다.
"무엇을 만드는지"의 근거는 CLAUDE.md에 있으므로, 이 문서는 "어떻게 나누고 연결하는지"에 집중한다.

## 1. 전체 데이터 흐름

```
┌─────────────────┐   ┌──────────────────┐
│ Open Bandit      │   │ Criteo Attribution│
│ Dataset (obp)    │   │ Dataset            │
└────────┬─────────┘   └─────────┬─────────┘
         │                       │
         ▼                       ▼
   src/cocoa/data/          src/cocoa/data/
   open_bandit_loader.py    criteo_loader.py
         │                       │
         ▼                       ▼
   time_split.py             delayed_conversion 학습용
   (train/eval 시간 분할)     클릭→전환 시차 분포 추출
         │                       │
         │                       ▼
         │              src/cocoa/reward/
         │              delayed_conversion.py
         │              (p(x), lam(x) 추정, soft label)
         │                       │
         └───────────┬───────────┘
                      ▼
         configs/reward_assumptions.yaml
                      │
                      ▼
         src/cocoa/reward/semisynthetic.py
         r = y_click*y_conv*price*commission*(1-y_cancel)
         E[r|x,a] = p_click*p_conv*price*commission*(1-cancel_rate)
                      │
         ┌────────────┴─────────────┐
         ▼                           ▼
src/cocoa/envs/                policies/ 학습·평가에
synthetic_env.py               직접 투입되는 보상 신호
(참 보상함수 보유,                     │
 obp.SyntheticBanditDataset 확장)      │
         │                            │
         ▼                            ▼
  evaluation/regret.py         src/cocoa/policies/*
  (H1, H2: 누적 후회)          Random/Greedy/eps-greedy/
                                LinUCB/Neural-Linear TS/
                                제안(지연·취소 보정 TS)
                                       │
                                       ▼
                          evaluation/ope_estimators.py
                          (IPS/SNIPS/DR, H3: random↔bts 교차검증)
                                       │
                                       ▼
                          evaluation/confidence_interval.py
                          (부트스트랩, 시드 10+)
                                       │
                                       ▼
                          evaluation/sensitivity.py
                          (reward_assumptions 격자 스윕, H4: Kendall tau)
                                       │
                                       ▼
                              scripts/report.py
                              results/*.csv, results/*.png
```

핵심 규칙(CLAUDE.md §6, §13): 합성 환경(참값 알 수 있음)과 실로그 기반 OPE(참값
모름)는 서로 다른 판정(H1/H2 vs H3)에 쓰이며 섞어서 결론 내지 않는다. 평가 기간
데이터는 `time_split.py`를 거친 뒤로는 학습·튜닝 경로에 절대 흘러들어가지 않는다.

## 2. 모듈 책임

### `src/cocoa/data/` — 데이터 로더·시간 분할
| 파일 | 책임 |
| --- | --- |
| `open_bandit_loader.py` | `obp`로 Open Bandit Dataset 로드. behavior_policy(`random`/`bts`) 선택, position(1/2/3, 실제 데이터 검증값) 유지 |
| `criteo_loader.py` | Criteo Attribution 원본 CSV 로드. 컬럼명은 실제 파일 확인 후 상수화 (추측 금지, CLAUDE.md §3) |
| `time_split.py` | 시간 기준 train/eval 분할. eval 시작 시점 이전 데이터만 학습에 노출되는지 검증하는 로직 포함 |
| `action_context.py` | (제휴 상품, 노출 위치) 행동 정의와 맥락 벡터 구성. position 1/2/3 ↔ 좌/중/우 대응표 |

### `src/cocoa/reward/` — 반합성 보상·지연 전환
| 파일 | 책임 |
| --- | --- |
| `assumptions.py` | `reward_assumptions.yaml` 로드·스키마 검증(가격/수수료율/취소율 누락 시 즉시 실패) |
| `semisynthetic.py` | 실현 보상 `r`과 기대 보상 `E[r\|x,a]` 계산 (CLAUDE.md §4 공식 그대로) |
| `delayed_conversion.py` | Criteo로 `p(x)`(전환확률), `lam(x)`(전환 속도) 추정. Chapelle(2014) soft label 계산, attribution window 종료 후 실값 교정 |

### `src/cocoa/envs/` — 합성 환경
| 파일 | 책임 |
| --- | --- |
| `synthetic_env.py` | `obp.dataset.SyntheticBanditDataset`를 감싸 참 보상함수를 노출. regret 계산의 기준값 제공 |
| `delay_cancel_wrapper.py` | Criteo에서 뽑은 지연 분포로 전환 시각을 샘플링하고 취소를 주입. 정책의 `update()`가 "클릭 즉시"와 "전환 확정 시"를 구분해 받도록 이벤트 스트림 생성 |

### `src/cocoa/policies/` — 정책
| 파일 | 책임 |
| --- | --- |
| `base.py` | `Policy` Protocol(`select`, `update`), `Feedback`/`Action` 데이터클래스 정의 |
| `random_policy.py`, `logging_policy.py` | Random, 데이터셋 원 정책 재생 |
| `greedy.py`, `epsilon_greedy.py` | 탐색 없음 / ε-탐욕 |
| `linucb.py` | Li et al. 2010 |
| `neural_linear_ts.py` | 기본 Neural-Linear TS (확정 전환만 학습에 반영) |
| `delay_cancel_ts.py` | 제안 방법. soft label로 미확정 표본도 학습에 반영 + 취소 확률 보정 |
| `ablation.py` | 제거 실험 두 변형(지연 보정만 제거 / 취소 보정만 제거). `delay_cancel_ts.py`를 상속해 플래그로 분기 |

모든 정책은 `select()`에서 propensity를 함께 반환한다(OPE 필수, CLAUDE.md §5).
TS 계열은 사후 샘플링을 K회 반복한 몬테카를로로 propensity를 근사한다.

### `src/cocoa/evaluation/` — 평가
| 파일 | 책임 |
| --- | --- |
| `regret.py` | 합성 환경 전용. 누적 후회 계산, H1/H2 판정 |
| `ope_estimators.py` | IPS/SNIPS/DR. 먼저 random 로그로 bts 가치를 추정해 실제 기록값과 오차 비교(추정량 검증) → 가장 정확한 추정량으로 제안 정책 평가(H3) |
| `confidence_interval.py` | 부트스트랩 CI. 신뢰구간 하한 계산 헬퍼 (하한>0일 때만 "개선" 판정하는 규칙을 여기서 강제) |
| `sensitivity.py` | `reward_assumptions.yaml`의 `sensitivity_grid`를 순회하며 정책 순위 Kendall tau 계산(H4) |
| `report.py` | 위 결과를 상대 지표(로깅 정책 대비 개선률)로만 표/그림화. 절대 금액 출력 금지 |

### `src/cocoa/utils/`
| 파일 | 책임 |
| --- | --- |
| `seed.py` | 모든 난수 초기화의 단일 진입점(numpy/torch/random) |
| `logging.py` | 실험 로그 포맷 통일 |
| `config.py` | yaml 로드 공통 헬퍼, 결과 파일에 설정+시드+git commit hash를 함께 기록하는 유틸 |

## 3. 핵심 계약 (인터페이스)

```python
# src/cocoa/policies/base.py
class Action(NamedTuple):
    item_id: str
    position: int  # 1, 2, 3 (Open Bandit Dataset 실제 값, 좌/중/우)

class Feedback(NamedTuple):
    context: np.ndarray
    action: Action
    propensity: float
    clicked: bool
    click_time: datetime | None
    converted: bool | None      # 미확정이면 None
    conv_time: datetime | None
    cancelled: bool | None

class Policy(Protocol):
    def select(self, context: np.ndarray, candidates: list[Action]) -> tuple[Action, float]: ...
    def update(self, feedback: Feedback) -> None:
        """클릭 시 1차 갱신, 전환/취소 확정 시 soft label → 실값으로 교정 갱신."""
```

`Feedback`은 클릭 시점과 확정 시점에 각각 한 번씩, 서로 다른 상태로 `update()`에
전달된다. 이 재호출 경로가 지연 보정 로직의 핵심이므로 `delay_cancel_wrapper.py`가
이벤트 순서(클릭 → [soft label 갱신 …] → 확정)를 보장해야 한다.

## 4. 실행 스크립트 (`scripts/`)

| 스크립트 | 역할 |
| --- | --- |
| `download_data.py` | Open Bandit/Criteo 원본을 `data/raw/`로 받는 절차 (수동 다운로드 링크 안내 + 배치 정리만, 크롤링 아님) |
| `fit_delay_model.py` | Criteo로 `p(x)`, `lam(x)` 학습 → `data/processed/`에 저장 |
| `train.py` | `configs/experiment/*.yaml` 한 개를 받아 정책들을 학습/시뮬레이션 |
| `evaluate.py` | 학습 결과에 대해 regret/OPE/CI 계산 |
| `run_sensitivity.py` | reward_assumptions 격자 스윕 실행 |
| `report.py` | `results/`의 표·그림 생성 |

모든 스크립트는 `--config`와 `--seed`(또는 설정 내 seed 목록)를 받고,
실행 시점의 git commit hash를 결과에 함께 기록한다(CLAUDE.md §9).

## 5. 테스트 매핑 (`tests/`)

핵심 로직은 CLAUDE.md §9가 명시한 대로 단위 테스트를 둔다.

- `test_time_split.py` — 분할 경계, eval 데이터가 학습 경로에 누수되지 않는지
- `test_reward.py` — `r`, `E[r|x,a]` 계산 공식 정확성 (극단값: click=0 → r=0 등)
- `test_delayed_conversion.py` — soft label 공식의 극한(e→0일 때 p(x)에 수렴, e→∞일 때 0에 수렴)
- `test_policies.py` — 각 정책의 propensity가 합리적 범위(0,1]에 있는지, `update()` 후 상태 변화
- `test_ope_estimators.py` — IPS/SNIPS/DR을 알려진 정답이 있는 장난감 예제로 검증
- `test_synthetic_env.py` — 참 보상함수와 관측 보상의 관계

## 6. 범위 경계 (재확인)

이 아키텍처는 CLAUDE.md §2의 범위만 다룬다. MDP/순차 RL, 제약 RL, 광고 채널
선택, LLM 문구 생성, 실서비스 연동은 이 구조에 포함하지 않는다. 새 모듈을
추가하기 전 범위 밖인지 먼저 확인한다.
