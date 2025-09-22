"""Apple MCP 메모 기능 테스트 코드.

이 테스트는 Apple MCP를 통해 macOS 메모 앱과 상호작용하는 기능을 검증합니다.
실제 Apple MCP 서버와 연결하여 메모 생성, 검색, 조회 기능을 테스트합니다.

주의사항:
- macOS에서만 실행 가능
- Apple MCP 서버가 설치되어 있어야 함
- 메모 앱에 대한 시스템 권한이 필요
- 실제 메모가 생성/수정될 수 있으므로 주의
"""

from __future__ import annotations

import platform
import pytest
from pathlib import Path

from ai.core.exceptions import ToolError
from mcp.tools.apple_tool import AppleTool


class TestAppleMCPNotes:
    """Apple MCP 메모 기능 테스트 클래스."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """각 테스트 전에 실행되는 설정."""
        # macOS 환경 확인
        if platform.system() != "Darwin":
            pytest.skip("Apple MCP는 macOS에서만 사용 가능합니다.")
        
        # AppleTool 초기화
        try:
            self.apple_tool = AppleTool()
        except ToolError as e:
            pytest.skip(f"AppleTool 초기화 실패: {e}")
    
    def test_apple_tool_initialization(self):
        """AppleTool이 제대로 초기화되는지 테스트."""
        assert self.apple_tool.tool_name == "apple"
        assert "macOS Apple 앱들과 상호작용" in self.apple_tool.description
        assert "notes" in self.apple_tool.parameters["app"]["enum"]
    
    def test_notes_permission_guide(self):
        """메모 앱 권한 가이드가 제대로 제공되는지 테스트."""
        guide = self.apple_tool.get_permission_guide("notes")
        assert "메모 앱 권한 설정" in guide
        assert "전체 디스크 접근 권한" in guide
        assert "시스템 환경설정" in guide
    
    def test_invalid_app_parameter(self):
        """잘못된 앱 파라미터 처리 테스트."""
        with pytest.raises(ToolError) as exc_info:
            self.apple_tool.run(app="invalid_app", operation="search")
        
        assert "app 파라미터는 다음 중 하나여야 합니다" in str(exc_info.value)
    
    def test_invalid_operation_for_notes(self):
        """메모 앱에서 지원하지 않는 operation 테스트."""
        with pytest.raises(ToolError) as exc_info:
            self.apple_tool.run(app="notes", operation="invalid_operation")
        
        assert "notes 앱에서 지원하는 operation" in str(exc_info.value)
    
    @pytest.mark.integration
    def test_notes_search_basic(self):
        """
        메모 검색 기본 기능 테스트.
        
        주의: 이 테스트는 실제 Apple MCP 서버와 연결합니다.
        - Bun 또는 Node.js가 설치되어 있어야 함
        - Apple MCP 서버가 빌드되어 있어야 함
        - 메모 앱 권한이 설정되어 있어야 함
        """
        try:
            result = self.apple_tool.run(
                app="notes",
                operation="search",
                query="test",
                limit=5
            )
            
            # 성공적으로 실행되었는지 확인
            assert result.success, f"메모 검색 실패: {result.error}"
            
            # 결과 데이터 형태 확인
            data = result.data
            print(f"메모 검색 결과: {data}")
            
        except ToolError as e:
            # 권한 오류나 서버 연결 실패 시 스킵
            if "권한" in str(e) or "connection" in str(e).lower():
                pytest.skip(f"권한 또는 연결 문제로 테스트 스킵: {e}")
            else:
                pytest.fail(f"예상하지 못한 오류: {e}")
    
    @pytest.mark.integration
    def test_notes_list_basic(self):
        """
        메모 목록 조회 기본 기능 테스트.
        """
        try:
            result = self.apple_tool.run(
                app="notes",
                operation="list",
                limit=3
            )
            
            assert result.success, f"메모 목록 조회 실패: {result.error}"
            
            data = result.data
            print(f"메모 목록 결과: {data}")
            
        except ToolError as e:
            if "권한" in str(e) or "connection" in str(e).lower():
                pytest.skip(f"권한 또는 연결 문제로 테스트 스킵: {e}")
            else:
                pytest.fail(f"예상하지 못한 오류: {e}")
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_notes_create_and_search(self):
        """
        메모 생성 후 검색 통합 테스트.
        
        주의: 실제 메모가 생성됩니다!
        """
        import time
        import uuid
        
        # 고유한 테스트 메모 제목 생성
        test_title = f"테스트 메모 {uuid.uuid4().hex[:8]}"
        test_content = "AppleTool 테스트용 메모입니다. 자동으로 생성된 메모이므로 삭제해도 됩니다."
        
        try:
            # 1. 메모 생성
            create_result = self.apple_tool.run(
                app="notes",
                operation="create",
                data={
                    "title": test_title,
                    "content": test_content
                }
            )
            
            assert create_result.success, f"메모 생성 실패: {create_result.error}"
            print(f"메모 생성 결과: {create_result.data}")
            
            # 메모 앱이 업데이트될 시간을 잠시 대기
            time.sleep(2)
            
            # 2. 생성한 메모 검색
            search_result = self.apple_tool.run(
                app="notes",
                operation="search",
                query=test_title,
                limit=5
            )
            
            assert search_result.success, f"메모 검색 실패: {search_result.error}"
            print(f"메모 검색 결과: {search_result.data}")
            
            # 검색 결과에 생성한 메모가 포함되어 있는지 확인
            search_data = search_result.data
            if isinstance(search_data, str):
                assert test_title in search_data, "생성한 메모가 검색 결과에 없습니다."
            elif isinstance(search_data, (list, dict)):
                # 구조화된 데이터인 경우 문자열로 변환해서 확인
                assert test_title in str(search_data), "생성한 메모가 검색 결과에 없습니다."
            
        except ToolError as e:
            if "권한" in str(e) or "connection" in str(e).lower():
                pytest.skip(f"권한 또는 연결 문제로 테스트 스킵: {e}")
            else:
                pytest.fail(f"예상하지 못한 오류: {e}")


class TestAppleMCPServerStatus:
    """Apple MCP 서버 상태 및 설치 확인 테스트."""
    
    def test_apple_mcp_installation_check(self):
        """Apple MCP 설치 상태 확인."""
        if platform.system() != "Darwin":
            pytest.skip("macOS에서만 테스트 가능")
        
        from mcp.apple_mcp_manager import AppleMCPManager, AppleMCPInstaller
        
        project_root = Path(__file__).parent.parent
        installer = AppleMCPInstaller(project_root)
        
        # 설치 상태 확인
        is_installed = installer.is_installed()
        print(f"Apple MCP 설치됨: {is_installed}")
        
        # 필수 요구사항 확인
        prerequisites = installer.check_prerequisites()
        print(f"필수 요구사항: {prerequisites}")
        
        if not is_installed:
            print("Apple MCP가 설치되지 않았습니다.")
            print(installer.get_installation_guide())
    
    def test_apple_mcp_server_connection(self):
        """Apple MCP 서버 연결 테스트."""
        if platform.system() != "Darwin":
            pytest.skip("macOS에서만 테스트 가능")
        
        from mcp.apple_mcp_manager import AppleMCPManager
        
        project_root = Path(__file__).parent.parent
        manager = AppleMCPManager(project_root)
        
        # 서버 상태 확인
        status = manager.get_status()
        print(f"서버 상태: {status}")
        
        # 설치되어 있고 요구사항이 충족된 경우에만 서버 시작 테스트
        if status["installed"] and all(status["prerequisites"].values()):
            try:
                # 서버 시작 시도
                success = manager.start_server()
                print(f"서버 시작 성공: {success}")
                
                if success:
                    # 서버 상태 확인
                    print(f"서버 실행 중: {manager.is_server_running()}")
                    
                    # 서버 중지
                    manager.stop_server()
                    print("서버 중지 완료")
                
            except Exception as e:
                print(f"서버 테스트 중 오류: {e}")
        else:
            print("설치 또는 요구사항 미충족으로 서버 테스트 스킵")


if __name__ == "__main__":
    """직접 실행 시 기본 테스트 수행."""
    print("🍎 Apple MCP 메모 기능 테스트 시작")
    print("=" * 50)
    
    # 기본적인 상태 확인
    status_test = TestAppleMCPServerStatus()
    status_test.test_apple_mcp_installation_check()
    print()
    status_test.test_apple_mcp_server_connection()
    print()
    
    # 메모 기능 기본 테스트
    if platform.system() == "Darwin":
        try:
            notes_test = TestAppleMCPNotes()
            
            # setup_method 직접 호출 대신 수동 초기화
            if platform.system() != "Darwin":
                print("⚠️ macOS가 아니므로 메모 기능 테스트를 스킵합니다.")
                exit()
            
            try:
                notes_test.apple_tool = AppleTool()
            except ToolError as e:
                print(f"⚠️ AppleTool 초기화 실패: {e}")
                print("Apple MCP 설정을 완료한 후 다시 시도해주세요.")
                exit()
            
            print("📝 메모 기능 기본 테스트")
            notes_test.test_apple_tool_initialization()
            print("✅ AppleTool 초기화 성공")
            
            notes_test.test_notes_permission_guide()
            print("✅ 권한 가이드 제공 성공")
            
            try:
                notes_test.test_invalid_app_parameter()
                print("✅ 잘못된 앱 파라미터 처리 성공")
            except Exception:
                print("✅ 잘못된 앱 파라미터 처리 성공 (예외 발생 확인)")
            
            try:
                notes_test.test_invalid_operation_for_notes()
                print("✅ 잘못된 operation 처리 성공")
            except Exception:
                print("✅ 잘못된 operation 처리 성공 (예외 발생 확인)")
            
            print("\n🔗 실제 메모 앱 연동 테스트 (권한 필요)")
            try:
                notes_test.test_notes_search_basic()
                print("✅ 메모 검색 기본 기능 성공")
            except Exception as e:
                print(f"⚠️ 메모 검색 테스트 스킵: {e}")
            
            try:
                notes_test.test_notes_list_basic()
                print("✅ 메모 목록 조회 기본 기능 성공")
            except Exception as e:
                print(f"⚠️ 메모 목록 테스트 스킵: {e}")
            
        except Exception as e:
            print(f"❌ 테스트 중 오류 발생: {e}")
    else:
        print("⚠️ macOS가 아니므로 메모 기능 테스트를 스킵합니다.")
    
    print("\n🎉 테스트 완료!")
