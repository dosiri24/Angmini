# Personal AI Assistant 사용 가이드 (MVP)

이 문서는 Phase 2.5 이후 연결된 ReAct 엔진을 CLI와 Discord 인터페이스에서 시험해보는 방법을 정리합니다.

---

## 1. 환경 준비 체크리스트
- `python -m pip install -r requirements.txt`
- `.env` 파일에 다음 값을 채워주세요.
- `DEFAULT_INTERFACE=cli` (또는 `discord`)
- `GEMINI_API_KEY=...` (필수)
- `GEMINI_MODEL=gemini-1.5-pro` (입력하지 않으면 자동으로 이 값이 사용됩니다. 만약 `models/...` 형식으로 적어도 자동으로 정리됩니다)
  - `DISCORD_BOT_TOKEN=...` (Discord 인터페이스 사용 시)
- Google Gemini를 호출할 수 있는 네트워크 환경인지 확인합니다.
- Discord 봇을 사용한다면 `pip install discord.py`가 완료되어 있는지 확인합니다.

⚠️ `GEMINI_API_KEY`가 비어 있으면 엔진이 초기화되지 않고 인터페이스에서 경고 메시지를 보여줍니다.

---

## 2. CLI에서 테스트해보기
1. `DEFAULT_INTERFACE=cli`로 설정한 상태에서 `python main.py`를 실행합니다.
2. 안내 메시지가 보이면 다음과 같이 질문을 입력해보세요.
   ```
   assistant> 내 홈 디렉터리 문서 폴더 목록 보여줘
   ```
3. 엔진이 계획을 세우고 파일 도구를 활용해 결과를 반환하면, CLI에 다음 정보가 출력됩니다.
   - 계획 체크리스트 (각 단계 상태 포함)
   - 실패 여부
   - 마지막 단계의 상세 결과(JSON 요약)
4. 작업을 마친 뒤에는 `assistant> exit`으로 종료할 수 있습니다.

문제가 발생하면 CLI에 `⚠️ 작업을 완료하지 못했어요: ...` 형태의 오류가 표시되고, 자세한 내용은 로그를 확인할 수 있습니다.

---

## 3. Discord 봇에서 테스트해보기
1. `.env`에서 `DEFAULT_INTERFACE=discord`로 지정하고, 유효한 `DISCORD_BOT_TOKEN`을 입력합니다.
2. `python main.py`를 실행하면 봇이 로그인합니다.
3. 테스트용 채널에서 봇에게 메시지를 보내보세요.
   ```
   내 다운로드 폴더 파일 목록 정리해줘
   ```
4. 봇은 입력을 GoalExecutor에 전달하여 동일한 ReAct 루프를 수행하고, 결과 요약을 답장으로 돌려줍니다.
   - 계획 요약과 수행된 단계들
   - 실패 로그가 있다면 마지막 시도 정보
   - 마지막 성공 단계의 결과 데이터 (JSON 요약)
5. 응답이 길면 자동으로 1,800자 근처에서 잘라서 전송합니다.

에러가 발생하면 봇은 경고 메시지를 전송하고, 서버 콘솔 로그에 상세한 스택 정보를 남깁니다.

---

## 4. FileTool 시나리오 수동 검증 팁
- 테스트용으로 임시 디렉터리를 만들고 `operation=list/read/write/move/trash` 다섯 가지를 모두 시도해보세요.
- `write` 작업 이후에는 실제로 파일이 생성되었는지 확인하고, CLI/Discord 메시지의 결과 JSON에 `bytes_written` 필드가 포함되는지 살펴보세요.
- `move` 작업은 `destination` 파라미터가 필요하며, 작업이 끝나면 파일이 새 경로로 이동했는지 확인하세요.
- `trash` 작업은 파일을 macOS 휴지통으로 옮기므로 테스트 시 임시 파일을 사용하고 즉시 비워도 됩니다.
- 동일한 명령을 반복 실행하면서 실패 로그가 어떻게 누적 표시되는지 확인하면 LoopDetector 동작을 간접적으로 검증할 수 있습니다.

이 과정을 따라가면 Phase 2.5 목표인 “인터페이스 ↔ ReAct 엔진 통합”이 정상적으로 작동하는지 빠르게 점검할 수 있습니다.
