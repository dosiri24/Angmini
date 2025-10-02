#!/usr/bin/env python
"""Apple MCP 테스트 스크립트"""

from mcp.apple_mcp_manager import AppleMCPManager
from pathlib import Path

def main():
    print("Apple MCP 테스트 시작...")

    # AppleMCPManager 생성
    manager = AppleMCPManager()

    # 상태 확인
    status = manager.get_status()
    print(f"설치 상태: {status['installed']}")
    print(f"서버 실행 중: {status['server_running']}")
    print(f"필수 요구사항: {status['prerequisites']}")

    # 서버 시작
    print("\n서버 시작 시도...")
    success = manager.start_server()

    if success:
        print("✅ 서버 시작 성공!")

        # 연결 테스트
        try:
            response = manager.send_request("tools/list", {}, timeout=10.0)
            print(f"도구 목록: {response}")
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")

        # 서버 종료
        manager.stop_server()
        print("서버 종료됨")
    else:
        print("❌ 서버 시작 실패")
        diagnostics = manager.get_runtime_diagnostics()
        print(f"진단 정보: {diagnostics}")

if __name__ == "__main__":
    main()