# Angmini 리팩토링 계획

## 개요
이 문서는 Angmini 프로젝트의 리팩토링 계획을 담고 있습니다. 주요 목적은:
- 불필요한 기능 제거
- 에이전틱 AI 핵심 목적에 집중
- 과도한 모듈화 억제 및 코드 단순화

## 1. 현재 프로젝트 상태 분석

### 핵심 목적
- **에이전틱 AI**: 자율적으로 작업을 수행하는 개인용 AI 어시스턴트
- **CrewAI 기반**: 멀티 에이전트 시스템으로 복잡한 작업 자동화
- **사용자 인터페이스**: CLI와 Discord를 통한 상호작용

### 현재 구조
```
프로젝트 규모:
- 총 파일: 130+ 파일
- 핵심 모듈: ai/ (에이전트, 메모리, crew, proactive)
- MCP 도구: mcp/tools/ (7개 도구)
- 인터페이스: CLI, Discord
- 외부 의존성: external/apple-mcp/ (git submodule)
```

## 2. 식별된 문제점

### 2.1 불필요한 기능 및 레거시 코드
1. **archive/react_engine/**: 전체 ReAct 엔진 (사용되지 않음)
   - 14개 파일의 구 아키텍처 코드
   - CrewAI로 완전히 대체되었으나 제거되지 않음

2. **중복된 설정 및 유틸리티**:
   - `ai/ai_brain.py`: AIBrain 클래스 (Gemini 초기화만 담당)
   - `ai/core/singleton.py`: 과도한 싱글톤 패턴 사용
   - `scripts/` 내 일회성 마이그레이션 스크립트들

### 2.2 과도한 모듈화 영역

#### 메모리 시스템 (14개 파일)
현재 구조가 지나치게 복잡:
```
ai/memory/
├── service.py           # 기본 서비스
├── memory_curator.py    # LLM 큐레이션
├── embedding.py         # 임베딩 생성
├── deduplicator.py      # 중복 제거
├── retention_policy.py  # 보존 정책
├── factory.py           # 팩토리 패턴
├── memory_records.py    # 데이터 모델
├── pipeline.py          # 파이프라인
├── snapshot_extractor.py # 스냅샷 추출
├── hybrid_retriever.py  # 하이브리드 검색
├── cascaded_retriever.py # 캐스케이드 검색
├── importance_scorer.py # 중요도 점수
├── metrics.py           # 메트릭
└── entity/              # 엔티티 추출 (5개 파일 더)
```

**문제점**:
- 14개 파일 → 3-4개로 통합 가능
- 여러 retriever 패턴이 혼재 (hybrid, cascaded)
- entity 추출 시스템은 거의 사용 안 됨

#### Proactive 시스템 (7개 파일)
Discord 전용 능동 알림:
```
ai/proactive/
├── scheduler.py          # 스케줄러
├── capacity_analyzer.py  # 용량 분석
├── advance_notifier.py   # 사전 알림
├── state_manager.py      # 상태 관리
├── message_formatter.py  # 메시지 포맷
├── llm_message_generator.py # LLM 메시지 생성
└── __init__.py
```

**문제점**:
- 단순 알림 기능에 7개 파일은 과도함
- 에이전틱 AI의 핵심 기능보다 부가 기능에 가까움

### 2.3 에이전틱 AI 목적에 위배되는 구현

1. **수동적인 도구 실행 구조**
   - 현재: 사용자 요청 → PlannerAgent → 작업 분배 → 도구 실행
   - 문제: 자율적 작업 수행이 아닌 단순 명령 실행

2. **제한적인 에이전트 자율성**
   - delegation이 제한적 (hierarchical mode에서만 부분 활성화)
   - 에이전트간 협업이 단방향적

3. **장기 목표 추적 부재**
   - 메모리는 과거 경험 저장에만 집중
   - 미래 목표나 진행 중 작업 추적 없음

4. **멀티모달 기능 미활용**
   - AnalyzerAgent와 멀티모달 도구들이 있지만 충분히 활용되지 않음
   - 다른 에이전트들과의 연계 부족

### 2.4 로그 분석을 통한 구조적 문제점

**분석 대상 로그**:
- `logs/20251007_150637.log` (3.8MB, 35,313줄)
- `logs/20251007_144356.log` (3.1MB, 33,656줄)
- `logs/20251007_132604.log` (438KB, 1,213줄)

#### 문제 1: Context 무한 축적 (Critical)
**현상**:
- CrewAI의 "Recent Insights" 섹션이 세션 중 계속 누적
- 이전 작업의 Thought/Final Answer가 다음 작업에 전부 포함
- 예시: 단순 "안녕" 인사에도 이전 PDF 분석 결과 전체가 컨텍스트에 포함

**로그 증거**:
```
# Useful context:
Recent Insights:
- Thought: 사용자가 첨부한 파일 내용을 확인해야 합니다...
  Final Answer: GPS 과제 분석 결과: ...
- Thought: 노션 데이터베이스에서 작업을 확인...
  Final Answer: 현재 진행 중인 작업 목록...
[계속 누적...]
```

**영향**:
- 토큰 낭비: 불필요한 컨텍스트가 매 LLM 호출마다 전송
- 추론 속도 저하: 컨텍스트 길이 증가로 인한 처리 지연
- 컨텍스트 윈도우 초과 위험: 장시간 세션에서 오류 발생 가능
- 작업 간 오염: 무관한 이전 작업 정보가 현재 작업 판단에 영향

**해결 필요성**: 🔴 긴급 (Phase 2에 추가 필요)

#### 문제 2: 과도한 DEBUG 로깅
**현상**:
- 단일 세션에 35,313줄의 로그 생성
- 모든 LLM 요청/응답의 전체 JSON 페이로드 로깅
- thoughtSignature 필드에 인코딩된 바이너리 데이터 포함

**로그 증거**:
```
DEBUG:litellm:... "content": "Thought: ...", "thoughtSignature": "[인코딩된 바이너리 데이터]"
DEBUG:litellm:... POST Request Sent from LiteLLM: [수백 줄의 JSON]
```

**영향**:
- 디스크 공간 낭비: 매 실행마다 수 MB의 로그 파일 생성
- 로그 분석 어려움: 중요한 정보가 노이즈에 묻힘
- I/O 부하: 과도한 파일 쓰기 작업

**해결 필요성**: 🟡 중요 (Phase 5에 추가)

#### 문제 3: Memory Context Pollution
**현상**:
- 서로 무관한 작업 간 메모리 컨텍스트 공유
- PlannerAgent → NotionAgent 위임 시 이전 PDF 분석 결과 포함
- 메모리 정리 로직 부재

**영향**:
- 에이전트 혼란: 현재 작업과 무관한 컨텍스트로 인한 잘못된 판단
- 작업 독립성 저해: 각 작업이 이전 작업에 의존하게 됨
- 멀티모달 데이터 오염: 이미지/PDF 분석 결과가 무관한 작업에 영향

**해결 필요성**: 🔴 긴급 (Phase 2에 추가)

## 3. 리팩토링 계획

### Phase 1: 불필요한 코드 제거 (1주차)
```bash
# 제거 대상
- archive/ 디렉토리 전체
- ai/ai_brain.py (Config 클래스와 중복)
- ai/core/singleton.py (과도한 싱글톤 패턴)
- ai/memory/entity/ 디렉토리
- ai/memory/snapshot_extractor.py
- ai/memory/hybrid_retriever.py
- ai/memory/importance_scorer.py
- scripts/migrate_memory_v2.py (일회성 마이그레이션)
- scripts/test_singleton.py (테스트 스크립트)
```

### Phase 2: 메모리 시스템 단순화 + Context 관리 개선 (2주차)

**통합 구조**:
```
ai/memory/
├── service.py      # 메인 서비스 (curator, deduplicator 통합)
├── storage.py      # 저장소 (SQLite + FAISS 통합)
├── retriever.py    # 검색 (cascaded만 유지)
└── models.py       # 데이터 모델
```

**변경 사항**:
- 14개 파일 → 4개 파일로 축소
- Entity 추출 제거
- Hybrid retriever 제거 (cascaded만 유지)
- Pipeline, Factory 패턴 제거 (직접 초기화)

**🔴 긴급 추가: Context 관리 메커니즘 구현**

1. **Recent Insights 정리 로직 추가** (ai/crew/crew_config.py)
   - 작업 완료 시 컨텍스트 자동 정리
   - 최대 컨텍스트 길이 제한 (예: 최근 3개 작업만 유지)
   - 작업 유형별 컨텍스트 분리 (멀티모달 분석 / 일반 작업)

2. **CrewAI Memory 설정 최적화**
   ```python
   # crew_config.py
   memory_config = {
       "memory": True,
       "memory_limit": 3,  # 최근 3개 작업만 유지
       "memory_type": "short_term",  # 장기 메모리는 별도 관리
   }
   ```

3. **작업 간 컨텍스트 격리**
   - 각 kickoff() 호출마다 새 컨텍스트 생성
   - 이전 작업 컨텍스트는 메모리 시스템에 저장
   - 필요 시 검색으로만 조회

4. **멀티모달 데이터 격리**
   - 이미지/PDF 분석 결과는 별도 저장소에 보관
   - AnalyzerAgent 결과를 다른 에이전트가 필요할 때만 명시적 조회
   - 자동 컨텍스트 포함 방지

### Phase 3: Proactive 시스템 단순화 (3주차)

**통합 구조**:
```
ai/proactive.py  # 단일 파일로 통합
```

**변경 사항**:
- 7개 파일 → 1개 파일
- 핵심 기능만 유지: 스케줄링, Notion 체크, Discord 알림
- 복잡한 분석 로직 제거

### Phase 4: 에이전틱 기능 강화 (4주차)

**1. 자율 작업 실행 모드 추가**
```python
# ai/autonomous/goal_tracker.py
class GoalTracker:
    """장기 목표 추적 및 자율 실행"""
    def set_goal(self, goal: str, deadline: datetime)
    def track_progress(self)
    def execute_next_step(self)
```

**2. 에이전트 자율성 강화**
- 모든 에이전트에 `allow_delegation=True` 기본값
- 에이전트간 직접 통신 채널 추가
- 작업 결과에 따른 자율적 다음 작업 결정

**3. 멀티모달 기능 강화**
- AnalyzerAgent를 중심으로 한 멀티모달 워크플로우 구축
- 이미지/PDF/문서 분석 결과를 다른 에이전트가 활용
- 자동 문서 요약 및 인사이트 추출
- 시각적 정보와 텍스트 정보 통합 처리

**4. 프로액티브 작업 제안**
- 사용자 패턴 학습
- 선제적 작업 제안
- 자동 실행 옵션

### Phase 5: 코드 정리 및 최적화 (5주차)

**1. 중복 코드 제거**
- Agent 클래스들의 공통 코드 BaseAgent로 통합
- MCP 도구 어댑터 패턴 단순화

**2. 설정 간소화**
- 환경 변수 최소화
- 기본값 최적화
- 불필요한 설정 옵션 제거

**3. 문서화**
- 새로운 아키텍처 문서 작성
- API 문서 업데이트
- 사용 예제 추가

**🟡 추가: 로깅 시스템 최적화**

1. **로그 레벨 조정** (ai/core/logger.py)
   - 기본 로그 레벨을 INFO로 변경 (현재 DEBUG)
   - LiteLLM 로그 필터링: 전체 JSON 페이로드 제외
   - thoughtSignature 바이너리 데이터 로깅 제외

2. **구조화된 로깅**
   ```python
   # 변경 전
   logger.debug(f"Full LLM request: {json.dumps(request)}")

   # 변경 후
   logger.info(f"LLM request: model={model}, tokens={token_count}")
   logger.debug(f"LLM request summary: {request_summary()}")  # 요약만
   ```

3. **로그 회전 정책**
   - 파일 크기 제한: 10MB
   - 최대 보관 파일 수: 5개
   - 압축 아카이브 지원

4. **선택적 상세 로깅**
   - 환경 변수 `LOG_VERBOSE=true`로 상세 로깅 활성화
   - 일반 사용 시에는 간결한 로그만 출력
   - 디버깅 필요 시에만 전체 페이로드 로깅

## 4. 예상 결과

### 코드 감소
- **파일 수**: 130+ → 70-80개 (40% 감소)
- **코드 라인**: 약 30-40% 감소 예상
- **복잡도**: 대폭 감소

### 성능 개선
- **시작 시간**: 더 빠른 초기화
- **메모리 사용**: 감소 (특히 장시간 세션)
- **LLM 추론 속도**: Context 정리로 20-30% 개선 예상
- **토큰 사용량**: Recent Insights 정리로 30-50% 절감
- **로그 파일 크기**: 35K줄 → 5-10K줄로 70% 감소
- **유지보수성**: 크게 향상

### 기능 개선
- **자율성**: 진정한 에이전틱 AI로 진화
- **멀티모달 처리**: 이미지, PDF, 문서 등 다양한 형태의 데이터 통합 분석
- **확장성**: 새 기능 추가가 더 쉬워짐
- **안정성**: 단순한 구조로 버그 감소

## 5. 리스크 및 대응 방안

### 리스크 1: 기존 기능 손실
- **대응**: 각 단계별 백업 및 테스트
- **롤백 계획**: Git 브랜치 전략 활용

### 리스크 2: 호환성 문제
- **대응**: 인터페이스 변경 최소화
- **마이그레이션 스크립트 제공**

### 리스크 3: 사용자 혼란
- **대응**: 명확한 변경 로그 제공
- **점진적 마이그레이션 가이드**

## 6. 실행 일정

| 주차 | 작업 내용 | 예상 시간 |
|------|-----------|-----------|
| 1주 | 불필요한 코드 제거 | 10시간 |
| 2주 | 메모리 시스템 단순화 + Context 관리 개선 🔴 | 20시간 (+5시간) |
| 3주 | Proactive 단순화 | 8시간 |
| 4주 | 에이전틱 기능 강화 | 20시간 |
| 5주 | 코드 정리 및 최적화 + 로깅 개선 🟡 | 15시간 (+3시간) |

**총 예상 시간**: 73시간 (약 2-3개월, 주당 5-8시간 작업 기준)

**긴급 작업 추가 사유**: 로그 분석 결과 발견된 Context 무한 축적 및 Memory Pollution 문제는 장시간 세션에서 시스템 안정성에 심각한 영향을 미치므로 Phase 2에서 우선 해결 필요

## 7. 성공 지표

### 정량적 지표
- [ ] 파일 수 40% 감소
- [ ] 코드 라인 30% 감소
- [ ] 테스트 커버리지 80% 이상 유지
- [ ] 시작 시간 50% 단축
- [ ] 🔴 토큰 사용량 30-50% 절감 (Context 정리)
- [ ] 🔴 장시간 세션 안정성 개선 (Context 윈도우 초과 방지)
- [ ] 🟡 로그 파일 크기 70% 감소 (35K줄 → 5-10K줄)

### 정성적 지표
- [ ] 새 개발자가 1일 내 코드베이스 이해 가능
- [ ] 새 기능 추가 시간 50% 단축
- [ ] 자율 작업 실행 가능
- [ ] 멀티모달 데이터 처리 워크플로우 완성
- [ ] 사용자 만족도 향상

## 8. 결론

이 리팩토링 계획은 Angmini를 진정한 에이전틱 AI로 진화시키는 것을 목표로 합니다. 불필요한 복잡성을 제거하면서도 핵심 기능인 멀티모달 처리 능력을 강화하여, 더 강력하고 유지보수가 쉬운 시스템을 만들 수 있을 것입니다.

**핵심 원칙**:
1. **단순함이 복잡함을 이긴다** (불필요한 부분만 제거)
2. **멀티모달 처리는 핵심 경쟁력** (AnalyzerAgent와 관련 도구 강화)
3. **에이전틱 AI의 본질에 집중** (자율성 강화)
4. **점진적이고 안전한 리팩토링**