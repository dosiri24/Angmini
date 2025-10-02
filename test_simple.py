#!/usr/bin/env python
"""간단한 Apple MCP 테스트"""

def main():
    # 1. Apple MCP 매니저 직접 테스트
    print("=" * 50)
    print("1. Apple MCP Manager 테스트")
    print("=" * 50)

    try:
        from mcp.apple_mcp_manager import AppleMCPManager
        manager = AppleMCPManager()
        print(f"✅ AppleMCPManager 생성 성공")

        # 서버 시작
        success = manager.start_server()
        print(f"✅ 서버 시작: {success}")

        if success:
            manager.stop_server()
            print(f"✅ 서버 종료 성공")
    except Exception as e:
        print(f"❌ Apple MCP Manager 테스트 실패: {e}")

    print("\n" + "=" * 50)
    print("2. CLI 초기화 함수 테스트")
    print("=" * 50)

    try:
        import logging
        from interface.cli import _initialize_apple_mcp_server

        logger = logging.getLogger("test")
        logger.setLevel(logging.DEBUG)

        _initialize_apple_mcp_server(logger)
        print("✅ CLI 초기화 함수 실행 완료")

    except Exception as e:
        print(f"❌ CLI 초기화 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()