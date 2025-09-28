# 🧠 Memory Maintenance & Observability Guide

이 문서는 장기 기억 모듈을 안정적으로 운영하기 위한 관찰 지표와 유지보수 절차를 요약합니다. 어려운 용어는 최대한 배제했으며, 필요한 경우 단계별로 따라 할 수 있도록 구성했습니다.

---

## 1. 관찰 포인트 한눈에 보기

| 구분 | 지표 | 의미 | 확인 방법 |
| --- | --- | --- | --- |
| 저장(Capture) | `attempts` | 이번 세션에서 메모리를 저장하려고 시도한 횟수 | `MemoryService.metrics.as_dict()["capture"]` |
|  | `stored` | 실제로 저장에 성공한 횟수 | 〃 |
|  | `duplicates` | 중복으로 판정돼 저장을 건너뛴 횟수 | 〃 |
|  | `success_rate` | 저장 성공률 (`stored / attempts`) | 〃 |
| 조회(Retrieval) | `requests` | MemoryTool이 호출된 횟수 | `MemoryService.metrics.as_dict()["retrieval"]` |
|  | `hit_rate` | 검색 성공률 (`matches > 0`) | 〃 |
|  | `avg_latency_ms` | 검색 평균 지연(ms) | 〃 |
|  | `operation_counts` | 각 operation별 호출 횟수 | 〃 |

> ℹ️ **로그로 확인하기** – capture/retrieval가 수행될 때마다 DEBUG 로그에 최신 통계가 출력됩니다. 장기 추이를 보고 싶다면 `.metrics.as_dict()`를 주기적으로 수집하여 대시보드로 보내면 됩니다.

---

## 2. 임베딩 갱신 & 모델 교체 절차

새로운 임베딩 모델을 적용하거나 파라미터를 크게 바꿀 때는 아래 순서를 따르세요.

1. **사전 체크**
   - `.env`에 지정된 모델/경로(`QWEN3_EMBEDDING_PATH`, `QWEN3_EMBEDDING_MODEL`)를 확인합니다.
   - `requirements.txt`가 새로운 모델을 지원하는지 점검합니다.
2. **실험용 인덱스 생성**
   - 별도 브랜치/환경에서 `tests/test_qwen3_embedding_vector_store.py`를 실행해 임베딩 품질과 인덱스 저장이 정상인지 확인합니다.
   - 필요 시 `MemoryRepository.rebuild_index()`(추후 확장 포인트)에 신규 인덱스 생성 로직을 추가합니다.
3. **점진적 전환**
   - 운영 데이터(`data/memory/`)를 백업합니다.
   - `MemoryRepository`에 임시 테이블 혹은 신규 인덱스 파일을 생성합니다.
   - `MemoryService.metrics`의 `hit_rate`와 `avg_latency_ms`를 모니터링하면서 품질 저하 여부를 확인합니다.
4. **구버전 정리**
   - 문제가 없다면 구버전 인덱스를 삭제하거나 보관 스토리지로 이동합니다.
   - 문서 (`docs/memory_maintenance.md`)에 적용 날짜와 모델 버전을 기록해 두면 좋습니다.

---

## 3. 데이터 정리 & 개인정보 보호 원칙

1. **보존 주기**
   - `MemoryRetentionPolicy`가 기본적으로 값이 낮은 기록은 저장하지 않도록 설계돼 있지만, 3개월에 한 번씩 `repository.list_all()`을 돌며 오래된 항목을 검토하세요.
   - 프로젝트 종료, 팀 변경 등 사용 목적이 사라진 메모리는 `MemoryRepository.delete(record_id)`로 정리합니다.

2. **민감 정보 취급**
   - 저장 전/후 `record.source_metadata`에서 이메일, 전화번호 등 민감 정보가 발견되면 즉시 마스킹하거나 삭제하세요.
   - 로그(`logs/*.log`)에도 민감 정보가 남지 않도록 필요 시 로깅 레벨을 `INFO` 이하로 낮추거나 필터를 추가하세요.

3. **사용자 요청 대응**
   - 사용자가 “내 기억을 지워줘”라고 요청하면, `MemoryTool`의 `analyze_patterns`로 관련 범위를 파악하고 `MemoryRepository.delete_many(...)`(추가 구현 포인트)를 사용해 일괄 삭제하세요.
   - 삭제 이력은 별도 감사 로그로 남겨두면 추후 문제가 생겼을 때 근거 자료가 됩니다.

4. **백업 & 감사**
   - 월 1회 이상 `data/memory/` 디렉터리를 백업하고 무결성 검사를 수행하세요.
   - `MemoryService.metrics`에서 이상치(예: `hit_rate` 급락, `duplicates` 급증)가 감지되면 즉시 원인을 분석합니다.

---

## 4. 빠른 점검 체크리스트

- [ ] `MemoryService.metrics.as_dict()`에서 저장/조회 지표가 정상 범위에 있는가?
- [ ] 신규 임베딩을 적용했다면 테스트와 백업 기록이 남아 있는가?
- [ ] 민감 정보가 로그나 메모리에 남아 있지 않은가?
- [ ] 백업 주기와 삭제 절차가 문서화되어 있는가?

이 네 가지만 주기적으로 점검해도 메모리 시스템은 안정적으로 운영될 수 있습니다. 더 궁금한 점이 있다면 언제든 `docs/` 폴더의 다른 자료를 확인하세요!
