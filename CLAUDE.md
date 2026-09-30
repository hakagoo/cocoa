# CLAUDE.md — COCOA 프로젝트 컨텍스트

이 파일은 AI 코딩 도우미(Claude Code 등)가 이 저장소에서 작업할 때 먼저 읽는 프로젝트 안내서다.
사람 개발자도 온보딩 문서로 사용할 수 있다.

## 1. 프로젝트 한 줄 요약

COCOA(COntent COmmercialization Optimization Agent)는 제휴 상품과 노출 위치를 고르는
Contextual Bandit 에이전트다. 보상은 수일 뒤 확정되고 일부는 취소되는 제휴 수수료이며,
실서비스 데이터 없이 공개 데이터만으로 학습하고 평가한다. 대학원 연구 프로젝트다.

## 2. 연구 범위 (반드시 지킬 것)

포함:
- 행동(action): (제휴 상품, 노출 위치) 조합. 위치는 3개(좌·중·우 = Open Bandit Dataset의 position 0, 1, 2)
- 문제 형태: 노출 단위 Contextual Bandit (선택이 다음 상태를 바꾸지 않는다고 가정)
- 보상: 지연·취소되는 반합성(semi-synthetic) 금전 보상
- 제안 방법: 지연·취소 보정 Neural-Linear Thompson Sampling

제외 (요청이 없으면 구현하지 말 것):
- MDP·순차 RL(PPO, CQL, IQL 등), 제약 RL(CMDP), 안전 쉴드
- 광고·스폰서 채널 선택, LLM 문구 생성, 콘텐츠 이해 모듈, 웹 크롤러
- 실서비스 로그, 서빙 API, 실제 블로그 연동

범위 밖 기능이 필요해 보이면 구현하지 말고 먼저 질문한다.

## 3. 데이터

실데이터는 사용할 수 없다. 아래 공개 데이터만 사용한다.

| 데이터 | 용도 | 비고 |
| --- | --- | --- |
| Open Bandit Dataset (ZOZOTOWN) | 주 실험, 오프폴리시 학습, OPE 정확도 검증 | `obp` 패키지로 로드. behavior policy가 `random`, `bts` 두 종류라 교차 검증 가능 |
| Criteo Attribution Modeling Dataset | 지연 전환 모델 학습, 지연 분포 추정 | 클릭·전환·전환 시각·비용 포함. 행동 확률 없음 |
| 합성 데이터 | 참 보상 함수를 아는 환경에서 누적 후회 계산 | `obp.dataset.SyntheticBanditDataset` 기반 + 지연·취소 로직 직접 추가 |

데이터 원본은 `data/raw/`에 두고 git에 커밋하지 않는다(.gitignore). 스키마와 컬럼명은
다운로드한 실제 파일을 열어 확인한 뒤 사용하고, 추측으로 컬럼명을 쓰지 않는다.

## 4. 보상 정의

반합성 금전 보상:

```
r = y_click * y_conv * price(a) * commission_rate[cat(a)] * (1 - y_cancel)
```

- `price`, `commission_rate`, `cancel_rate`는 가정 값이다. 하드코딩하지 말고 `configs/reward_assumptions.yaml`에서만 읽는다.
- 선택 시점에는 `y_conv`, `y_cancel`이 관측되지 않는다. 기대 보상은 다음을 쓴다.

```
E[r | x, a] = p_click(x, a) * p_conv(x, a) * price(a) * commission_rate[cat(a)] * (1 - cancel_rate[cat(a)])
```

- 지연 보정(Chapelle, 2014): 클릭 후 경과 시간 e 동안 전환이 없는 미확정 표본은 0으로 두지 않고
  soft label을 쓴다.

```
P(conv=1 | 미확정, x, e) = p(x) * exp(-lam(x) * e) / (1 - p(x) + p(x) * exp(-lam(x) * e))
```

- 전환이 확정되거나 관측 기간(attribution window)이 끝나면 실제 값으로 교정한다.

## 5. 알고리즘

비교 대상(모두 같은 인터페이스로 구현):
1. Random, Logging policy(데이터셋의 원래 정책)
2. Greedy(기대 수수료 최대, 탐색 없음)
3. epsilon-greedy, LinUCB
4. 기본 Neural-Linear Thompson Sampling (확정된 전환만 학습)
5. 제안: 지연·취소 보정 Neural-Linear TS
6. 제거 실험: 지연 보정만 제거, 취소 보정만 제거

정책 인터페이스(예시, 필요 시 조정):

```python
class Policy(Protocol):
    def select(self, context: np.ndarray, candidates: list[Action]) -> tuple[Action, float]:
        """행동과 그 선택 확률(propensity)을 함께 반환한다."""
    def update(self, feedback: Feedback) -> None:
        """클릭 즉시 1차 갱신, 전환·취소 확정 시 교정 갱신."""
```

- 모든 정책은 선택 확률(propensity)을 반환해야 한다. OPE에 필수다.
- Thompson Sampling의 선택 확률은 사후 샘플링 몬테카를로로 근사한다.

## 6. 평가 원칙 (가장 중요)

이 프로젝트는 "실제로 돈을 벌었다"를 주장하지 않는다. "가정된 수익 구조에서 기존 정책보다
기대 보상이 높다"를 신뢰구간과 함께 주장한다.

1. 시간 기준 분할: 앞 기간 = 학습, 뒤 기간 = 평가. 평가 셋은 학습·튜닝에 절대 쓰지 않는다.
2. 하이퍼파라미터 튜닝은 학습 기간 안의 검증 셋으로만 한다.
3. 참값 평가: 합성 데이터에서 누적 후회(cumulative regret)를 계산한다. H1, H2 판정.
4. 검증된 OPE: Open Bandit의 `random` 로그로 `bts` 정책 가치를 추정해 실제 기록 값과 비교하고,
   IPS / SNIPS / DR 추정량의 오차를 먼저 측정한다. 가장 정확한 추정량으로 제안 정책을 평가한다. H3 판정.
5. 신뢰구간 하한(95%)이 0보다 클 때만 "개선"이라고 보고한다.
6. 민감도 분석: `reward_assumptions.yaml`의 값을 격자로 바꿔 정책 순위(Kendall tau)를 확인한다. H4 판정.
7. 무작위 시드 10개 이상, 부트스트랩 신뢰구간을 보고한다.
8. 학습에 쓴 환경의 점수만으로 결론을 내리지 않는다(순환 평가 금지).

결과는 절대 금액이 아니라 상대 지표(로깅 정책 대비 개선률, 누적 후회)로 보고한다.

## 7. 저장소 구조 (권장)

```
cocoa/
  CLAUDE.md
  README.md
  pyproject.toml
  configs/
    reward_assumptions.yaml   # 가격·수수료율·취소율 가정 (비개발자 팀원이 조사해 채움)
    experiment/*.yaml         # 실험별 설정 (데이터, 정책, 시드)
  data/
    raw/                      # 원본 (git 제외)
    processed/                # 전처리 결과 (git 제외)
  src/cocoa/
    data/                     # 데이터 로더, 시간 분할, 행동·맥락 대응
    reward/                   # 반합성 보상, 지연 전환 모델
    policies/                 # 정책 구현 (공통 인터페이스)
    envs/                     # 합성 환경 (지연·취소 포함)
    evaluation/               # 후회 계산, OPE, 신뢰구간, 민감도 분석
    utils/                    # 시드 고정, 로깅
  scripts/                    # 실행 스크립트 (학습, 평가, 표·그림 생성)
  notebooks/                  # 탐색용. 최종 결과는 scripts로 재현 가능해야 함
  results/                    # 실험 결과 (CSV, 그림)
  tests/
```

## 8. 기술 스택

- Python (버전은 `obp` 호환 범위를 확인해 고정)
- numpy, pandas, scikit-learn, PyTorch
- obp (Open Bandit Pipeline): 데이터 로드, 합성 데이터, OPE 추정량
- matplotlib (결과 그림), pyyaml (설정), pytest (테스트)

새 라이브러리를 추가하기 전에 이유를 설명하고 확인을 받는다.

## 9. 코딩 규칙

- 개발자는 Java/Spring 경력자이며 ML·강화학습은 학습 중이다.
  ML 개념이 들어가는 코드에는 "무엇을, 왜" 하는지 짧은 한국어 주석을 단다.
- 복잡한 추상화보다 읽기 쉬운 코드를 우선한다. 한 함수는 한 가지 일만 한다.
- 타입 힌트를 쓴다. 공개 함수에는 docstring을 쓴다.
- 모든 실험은 설정 파일 + 시드로 재현 가능해야 한다. 난수는 `utils`의 시드 함수로만 초기화한다.
- 가정 값, 경로, 하이퍼파라미터를 코드에 하드코딩하지 않는다.
- 결과 파일에는 실험 설정, 시드, git 커밋 해시를 함께 기록한다.
- 핵심 로직(보상 계산, 지연 보정 soft label, propensity 계산, OPE 추정량, 시간 분할)에는 단위 테스트를 작성한다.
- 평가 셋 누수(leakage)가 생길 수 있는 변경은 반드시 먼저 알린다.

## 10. 작업 순서 (1단계 로드맵)

1. 데이터 로더와 시간 분할 (Open Bandit, Criteo)
2. `reward_assumptions.yaml` 스키마와 반합성 보상 계산
3. 지연 전환 모델 (Criteo로 p(x), lam(x) 추정)
4. 합성 환경 (지연·취소 포함, Criteo 지연 분포 사용)
5. 베이스라인 정책 (Random, Greedy, epsilon-greedy, LinUCB)
6. Neural-Linear TS, 지연·취소 보정 TS
7. 평가: 누적 후회, OPE 정확도 검증, OPE 기반 정책 평가, 신뢰구간
8. 민감도 분석과 결과 표·그림 생성 스크립트

## 11. 용어

| 용어 | 뜻 |
| --- | --- |
| Contextual Bandit(컨텍스추얼 밴딧) | 맥락을 보고 행동 하나를 고른 뒤 보상을 관측하는 문제. 선택이 다음 상태를 바꾸지 않음 |
| Propensity(선택 확률) | 로깅 정책이 그 행동을 고른 확률. OPE에 필수 |
| OPE(Off-Policy Evaluation) | 기존 로그만으로 새 정책의 가치를 추정 |
| IPS / SNIPS / DR | OPE 추정량. 역확률 가중 / 자기정규화 IPS / 이중 강건 |
| Regret(후회) | 최적 정책 대비 잃은 보상. 참값을 아는 합성 환경에서만 계산 가능 |
| Delayed feedback(지연 피드백) | 전환이 클릭 후 한참 뒤에 확정되는 현상 |
| Semi-synthetic reward(반합성 보상) | 실제 클릭 로그 위에 가정한 가격·수수료율을 곱한 보상 |
| Logging policy(로깅 정책) | 데이터를 수집할 때 실제로 쓰인 정책 |

## 12. 참고 문헌 (구현 시 참조)

- Chapelle (2014) Modeling delayed feedback in display advertising, KDD — 지연 전환 모델
- Riquelme et al. (2018) Deep Bayesian bandits showdown, ICLR — Neural-Linear TS
- Li et al. (2010) LinUCB, WWW
- Dudík et al. (2011) Doubly robust policy evaluation and learning, ICML
- Swaminathan & Joachims (2015) CRM, JMLR — 오프폴리시 정책 학습
- Saito et al. (2021) Open Bandit Dataset and Pipeline, NeurIPS Datasets and Benchmarks
- Thomas et al. (2015) High-confidence off-policy evaluation, AAAI
- Diemert et al. (2017) Criteo Attribution dataset, AdKDD

## 13. 하지 말 것

- 실서비스 데이터, 개인정보, 크롤링한 타인 콘텐츠를 저장소에 넣지 않는다.
- 평가 기간 데이터로 학습하거나 튜닝하지 않는다.
- 합성 환경 점수만으로 "성능 향상"을 결론 내리지 않는다.
- 결과를 원 단위 절대 수익으로 보고하지 않는다.
- 범위 밖 기능(2장)을 임의로 추가하지 않는다.
