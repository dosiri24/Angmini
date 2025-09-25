# Apple Tool 가이드

이 문서는 Apple MCP 연동 기능을 사용할 때 필요한 준비 사항과 운영 체크리스트를 정리했습니다. macOS에서만 동작하며, CLI/Discord 양 인터페이스에서 동일한 흐름을 따릅니다.

## 1. 준비 사항
- macOS 13 이상
- [Bun](https://bun.sh) 런타임 설치 (`bun --version` 확인)
- `external/apple-mcp` 디렉터리에 `bun install && bun run build` 수행
- 시스템 설정 > 개인정보 보호 및 보안에서 다음 권한 허용
  - 자동화(Automation) · 전체 디스크 접근 · 연락처 · 캘린더 · 미리알림 · 위치 서비스(지도용)

## 2. 빠른 시작 절차
1. `.venv` 활성화 후 `python main.py` 실행
2. CLI가 뜨면 Apple MCP 사전 시작 메시지가 표시되는지 확인
3. `notes search 프로젝트` 같은 명령을 입력해 응답을 확인
4. 필요한 경우 `mcp/apple_mcp_manager.py`의 `AppleMCPManager.get_status()`로 설치/재시작 상태 점검

## 3. 수동 검증 시나리오
### 3.1 CLI 체크리스트
- `notes search 회의` → 결과 목록이 정상 출력되는지
- `reminders list` → Apple MCP 서버가 유지되며 다른 앱도 동작하는지
- 네트워크를 잠시 끊었다가 `notes search` 반복 → 자동 재시작 로그 확인
- `exit` 입력 후 `AppleMCPManager.get_status()` 호출 → `restart_count`가 기대대로 증가했는지 확인

### 3.2 Discord 체크리스트
1. Discord 봇 환경변수를 설정하고 `python main.py --interface=discord` 실행
2. 테스트 채널에서 `notes search TODO` 명령 입력
3. 응답이 30초 이내 도착하는지, 실패 시 오류 메시지가 명확한지 확인
4. AppleTool의 `get_performance_metrics()`를 호출해 누적 요청 수를 기록

## 4. 장애·부하 테스트 메모
- 타임아웃: `mcp/tools/apple_tool.py`에서 `inspect_configuration()`을 호출하면 앱/연산별 타임아웃과 재시도 횟수를 확인할 수 있습니다.
- 보안 차단: 금지 패턴에 걸리는 입력(예: `sudo rm -rf /`)을 주고 `보안 검증 실패`가 반환되는지 확인
- 재시작 진단: `AppleMCPManager.get_runtime_diagnostics()` → `process_manager.last_restart_error`로 최근 오류 확인
- 부하 테스트: 동일한 노트 검색 명령을 20회 연속 호출한 뒤 평균 응답 시간(`get_performance_metrics()`의 `average_duration`)을 기록

## 5. 문제 해결
| 증상 | 점검 항목 |
| ---- | -------- |
| 서버가 시작되지 않음 | `docs/APPLE_TOOL_GUIDE.md`의 준비 사항, Bun 설치, 권한 설정 |
| 특정 앱만 실패 | 해당 앱 권한, AppleTool 로그(`security`/`timeout` 경고) |
| 빈번한 재시작 | `AppleMCPManager.get_status()`의 `restart` 정보를 확인, `MAX_RESTARTS` 조정 고려 |

## 6. 참조 함수 빠른 링크
- `AppleTool.inspect_configuration()` → 현재 타임아웃/보안 설정 요약
- `AppleTool.get_performance_metrics()` → 누적 성능 지표
- `AppleMCPManager.get_status()` → 서버 실행 여부 및 재시작 카운터
- `AppleMCPManager.get_runtime_diagnostics()` → 설치 및 프로세스 상태 상세

필요 시 `tests/test_apple_tool_integration.py`의 스켈레톤을 따라 수동 테스트를 진행하세요.
