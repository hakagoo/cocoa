# 데이터 준비 절차 (T0.4)

CLAUDE.md §3의 원칙을 따른다: 실데이터는 쓰지 않고, 아래 두 공개 데이터셋만
쓴다. 원본은 `data/raw/`에 두고 git에 커밋하지 않는다(`.gitignore`에 이미
반영됨). **아래 표시된 컬럼명·구조는 추측이 아니라 실제로 내려받아 연 파일
기준으로 검증한 값이다(검증일 2026-09-30).**

## 1. Open Bandit Dataset

- 공식 페이지: https://research.zozo.com/data.html
- 직접 다운로드 링크(등록·약관 동의 불필요): `https://research.zozo.com/data_release/open_bandit_dataset.zip`
- 라이선스: **CC BY 4.0** (저작자 표시만 하면 자유 이용). 사용 시 다음 논문 인용 요청:
  Saito, Aihara, Matsutani, Narita. "A Large-scale Open Dataset for Bandit Algorithms." arXiv:2008.07146 (2020)
- 크기: 약 394MB (zip), 2026-09-30 `curl -I` 확인 기준 `Content-Length: 412931917`.
  배포처가 파일을 교체하면 달라질 수 있다.

### 받는 방법

```bash
python scripts/download_data.py --dataset open_bandit
```

`data/raw/open_bandit_dataset/`에 압축을 풀고, zip 안에 있는 불필요한 감싸는
폴더 한 겹은 스크립트가 자동으로 걷어낸다.

### 실제 검증된 디렉토리 구조

```
data/raw/open_bandit_dataset/
  README                  # ZOZO가 배포한 원본 설명 (아래 "문서-실제 불일치" 참고)
  VERSION                 # "08/18/2020 Open Bandit Dataset 1.0"
  bts/
    all/{all.csv, item_context.csv}
    men/{men.csv, item_context.csv}
    women/{women.csv, item_context.csv}
  random/
    all/{all.csv, item_context.csv}
    men/{men.csv, item_context.csv}
    women/{women.csv, item_context.csv}
```

`obp.dataset.OpenBanditDataset(behavior_policy=..., campaign=..., data_path=...)`의
`data_path`에는 `data/raw/open_bandit_dataset`을 그대로 넘기면 된다
(obp 소스 `obp/dataset/real.py` 기준: `data_path / behavior_policy / campaign / f"{campaign}.csv"`를 읽음).

### 실제 검증된 컬럼 (campaign.csv, 예: `bts/all/all.csv` 헤더 그대로)

```
(무명 인덱스 열), timestamp, item_id, position, click, propensity_score,
user_feature_0, user_feature_1, user_feature_2, user_feature_3,
user-item_affinity_0 ... user-item_affinity_{N-1}
```

- `all` 캠페인: `user-item_affinity_0`~`_79` (80개, item 수와 동일)
- `men` 캠페인: `user-item_affinity_0`~`_33` (34개)
- `women` 캠페인: `user-item_affinity_0`~`_45` (46개)
- 첫 컬럼은 헤더 이름이 없는 pandas 인덱스 컬럼이다(`to_csv()` 기본 옵션으로
  저장된 흔적). 로더에서 `index_col=0`으로 읽거나 버릴 것.

`item_context.csv` 컬럼: `item_id, item_feature_0, item_feature_1, item_feature_2, item_feature_3`.

### item_id 범위 (item_context.csv 실제 행 수로 검증, 헤더 제외)

| 캠페인 | 행 수(=아이템 수) | item_id 범위 |
| --- | --- | --- |
| all | 80 | 0–79 |
| men | 34 | 0–33 |
| women | 46 | 0–45 |

### ⚠️ 문서-실제 불일치 (실제 파일 기준으로 판단할 것)

1. **zip 안에 들어있는 `README` 파일 자체가 "item_id ranges from 0-80"
   (all), "0-46"(women)이라고 적어 두었지만, 실제 `item_context.csv` 행 수는
   이와 다르다(위 표 참고: all은 0–79, women은 0–45).** ZOZO가 배포한
   README의 프로즈 설명보다 실제 파일을 신뢰해야 한다는 CLAUDE.md §3 원칙이
   그대로 들어맞는 사례.
2. GitHub `obp` 저장소의 `obd/README.md`(작은 샘플 데이터용 문서)는
   propensity 컬럼을 `action_prob`이라 적고 있지만, **실제 전체 데이터의
   컬럼명은 `propensity_score`다.** 샘플용 문서를 참고하지 말 것.
3. **원본 CSV의 `position` 컬럼값은 1, 2, 3이다 (좌/중/우)** — 두 캠페인
   파일에서 `cut -d',' -f4 ... | sort -u`로 직접 확인. 처음엔 이걸 근거로
   CLAUDE.md §2를 "position 1/2/3"으로 고쳤었는데, 그건 **틀린 정정이었다.**
   `obp.dataset.OpenBanditDataset.load_raw_data()`(obp/dataset/real.py:171)가
   `rankdata(data["position"], "dense") - 1`로 원본 1/2/3을 **자동으로 0/1/2로
   정규화**한다 — 실제로 obp로 로드해서 재확인함(2026-09-30). CLAUDE.md §3이
   "obp 패키지로 로드"를 명시하므로, 파이프라인이 실제로 다루는 값은 obp를 거친
   **0/1/2가 맞고, CLAUDE.md §2의 원래 표기가 옳았다.** 최종적으로 CLAUDE.md §2는
   0/1/2로 되돌리되 이 정규화 사실을 각주로 남겼다. `open_bandit_loader.py`(T1.1)를
   obp가 아닌 다른 경로로 원본 CSV를 직접 읽는 방식으로 바꾼다면 이 변환이
   없다는 것을 잊지 말 것.
4. README는 "user feature 0-4"(5개로 읽힐 수 있는 표현)라고 적었지만 실제
   컬럼은 `user_feature_0`~`_3`, 4개뿐이다.

## 2. Criteo Attribution Modeling for Bidding Dataset

- 공식 페이지: https://ailab.criteo.com/criteo-attribution-modeling-bidding-dataset/
- 문서에 적힌 다운로드 링크: `http://go.criteo.net/criteo-research-attribution-dataset.zip`
  — **2026-09-30 기준 반복 확인 결과 이 링크는 HTTP 404를 반환한다(끊겼거나
  이전됨).** 이 프로젝트에서는 이 링크를 자동화하지 않는다. `scripts/download_data.py --dataset criteo`는
  수동 절차 안내만 출력한다.
- 라이선스: **CC BY-NC-SA 4.0 (비영리 조건 있음)**. 대학원 연구 목적이라
  통상 문제 없어 보이지만, 재배포·상업적 활용 계획이 있다면 라이선스 조건을
  먼저 확인할 것.
- 파일 형식(공식 페이지 기재): `criteo_attribution_dataset.tsv.gz`, 압축
  623MB, tab-separated.

### 받는 방법 (현재는 수동)

1. https://ailab.criteo.com/criteo-attribution-modeling-bidding-dataset/ 에
   접속해 현재 유효한 다운로드 링크를 확인한다(위 공식 링크가 죽어 있으므로
   페이지에 갱신된 링크나 안내가 있는지 먼저 볼 것).
2. 받은 `criteo_attribution_dataset.tsv.gz`를 `data/raw/criteo_attribution/`에 둔다.
3. 압축을 풀기 전, 파일 크기와 체크섬(제공되면)을 페이지 기재값과 대조한다.

**Kaggle/HuggingFace 등에 올라온 미러본은 Criteo의 공식 배포가 아니고
원본과 동일한지 검증되지 않았다.** 부득이하게 미러를 쓸 경우, 아래 컬럼
스키마·행 수와 대조해 원본과 일치하는지 반드시 확인 후 사용한다.

### 컬럼 스키마 (공식 페이지 설명 기준 — 실제 파일로 아직 교차검증 못함, 공식 링크가 죽어 있어서)

| 컬럼 | 설명 |
| --- | --- |
| `timestamp` | 노출 시각(0부터 시작, 시간순 정렬) |
| `uid` | 사용자 식별자 |
| `campaign` | 캠페인 식별자 |
| `conversion` | 노출 후 30일 내 전환 발생 시 1. 음성 클래스 표기가 0인지 -1인지는 출처마다 다르게 설명함 — **실제 파일로 재확인 필요** |
| `conversion_timestamp` | 전환 시각, 없으면 -1 |
| `conversion_id` | 전환 식별자, 없으면 -1 |
| `attribution` | 해당 전환이 Criteo에 귀속되면 1 |
| `click` | 클릭 여부 |
| `click_pos` | 전환 전 클릭 위치(0=최초 클릭) |
| `click_nb` | 클릭 수 |
| `cost` | 변환된(실제 금액 아님) 노출 비용 |
| `cpo` | 변환된 전환당 비용 |
| `time_since_last_click` | 마지막 클릭 이후 경과 초 |
| `cat1`–`cat9` | 익명화된 범주형 맥락 특성 9개 |

**주의: 이 표는 공식 페이지 설명을 옮긴 것이지, 실제 파일을 열어 확인한
것이 아니다(다운로드 링크가 죽어 있어 아직 못 받음).** CLAUDE.md §3
원칙대로, 실제 파일을 구한 뒤 헤더와 dtype을 직접 열어 이 표와 대조하고
`data/criteo_loader.py`(T1.2) 구현 전에 반드시 갱신할 것 — 이 표의 컬럼명을
그대로 코드에 하드코딩하지 말 것.

## 다음 단계

- [ ] Criteo 공식 페이지에서 현재 유효한 다운로드 링크 확인 후 수동으로 받기
- [ ] Criteo 실제 파일을 열어 위 컬럼 스키마 표를 검증·갱신
- [x] CLAUDE.md §2의 position 표기 검증 — obp 로더가 원본 1/2/3을 0/1/2로
      정규화함을 실제로 확인, CLAUDE.md §2는 0/1/2 그대로 유지 (2026-09-30)
- [ ] Phase 1(T1.1, T1.2)에서 이 문서의 구조를 바탕으로 실제 로더 구현
