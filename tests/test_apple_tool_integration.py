"""Manual integration checklist for AppleTool.

이 파일은 macOS 환경에서 Apple MCP와 실제로 연동할 때 참고하는 스켈레톤입니다.
CI나 기본 테스트 러너에서는 항상 스킵됩니다.
"""

from __future__ import annotations

import platform

import pytest


@pytest.mark.integration
@pytest.mark.skipif(platform.system() != "Darwin", reason="AppleTool manual test requires macOS")
def test_manual_cli_scenario() -> None:
    """수동으로 AppleTool을 검증할 때 따라갈 체크리스트.

    1. `python main.py`로 CLI를 띄운 뒤, `notes search 프로젝트` 명령을 실행해 결과가 오는지 확인합니다.
    2. 동일한 세션에서 `reminders list` 등을 시도해 Apple MCP 서버가 유지되는지 확인합니다.
    3. 중간에 Wi-Fi를 끊었다가 다시 연결하여 자동 재시작 로그가 남는지 점검합니다.
    4. 완료 후에는 `exit`로 종료하고, `AppleMCPManager.get_status()`를 호출해 재시작 카운터를 확인합니다.
    """
    pytest.skip("수동 테스트 전용 시나리오입니다.")
