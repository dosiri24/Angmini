"""
개선된 AppleTool의 성능 최적화 및 안정성 기능 테스트.

기존 도구 시스템을 활용하여 추가된 기능들을 검증합니다:
- 성능 메트릭 수집
- 보안 검증
- 타임아웃 및 재시도
- 배치 처리
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from mcp.tools.apple_tool import AppleTool, PerformanceMetrics


class TestImprovedAppleTool:
    """개선된 AppleTool 테스트 클래스."""
    
    @pytest.fixture
    def mock_apple_tool(self, tmp_path):
        """Mock된 AppleTool 인스턴스."""
        external_dir = tmp_path / "external" / "apple-mcp"
        external_dir.mkdir(parents=True)
        
        # package.json 생성
        import json
        with open(external_dir / "package.json", "w") as f:
            json.dump({"name": "apple-mcp", "scripts": {"start": "node index.js"}}, f)
        
        with patch('platform.system', return_value='Darwin'):
            tool = AppleTool(project_root=tmp_path)
            
            # Apple MCP 관리자 mock
            tool._manager = MagicMock()
            tool._manager.is_server_running.return_value = True
            tool._manager.send_request.return_value = {
                "content": [{"text": "Mock response"}]
            }
            tool._installer.is_installed = MagicMock(return_value=True)
            tool._installer.check_prerequisites = MagicMock(return_value={
                "bun": True,
                "macos": True,
                "apple_mcp_path": True,
            })
            
            return tool

    def test_performance_metrics_initialization(self, mock_apple_tool):
        """성능 메트릭 초기화 테스트."""
        metrics = mock_apple_tool.get_performance_metrics()
        
        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0
        assert metrics["success_rate"] == 0.0
        assert metrics["average_duration"] == 0.0
        assert metrics["retry_count"] == 0

    def test_security_validation_dangerous_patterns(self, mock_apple_tool):
        """위험한 패턴 보안 검증 테스트."""
        # 위험한 패턴이 포함된 파라미터
        dangerous_params = {
            "app": "notes",
            "operation": "create",
            "data": {
                "content": "do shell script 'rm -rf /'"
            }
        }
        
        violations = mock_apple_tool._validate_security(dangerous_params)
        assert len(violations) > 0
        assert any("위험한 패턴" in v for v in violations)

    def test_security_validation_text_length(self, mock_apple_tool):
        """텍스트 길이 제한 보안 검증 테스트."""
        # 너무 긴 텍스트
        long_text = "x" * 15000  # 기본 제한 10000보다 큰 값
        
        params = {
            "app": "notes",
            "operation": "create",
            "data": {"content": long_text}
        }
        
        violations = mock_apple_tool._validate_security(params)
        assert len(violations) > 0
        assert any("텍스트가 너무 깁니다" in v for v in violations)

    def test_security_validation_clean_input(self, mock_apple_tool):
        """안전한 입력에 대한 보안 검증 테스트."""
        clean_params = {
            "app": "notes",
            "operation": "create",
            "data": {
                "title": "Test Note",
                "content": "This is a safe note content."
            }
        }
        
        violations = mock_apple_tool._validate_security(clean_params)
        assert len(violations) == 0

    def test_run_with_security_violation(self, mock_apple_tool):
        """보안 위반 시 run 메서드 동작 테스트."""
        result = mock_apple_tool.run(
            app="notes",
            operation="create",
            data={"content": "sudo rm -rf /"}
        )
        
        assert result.success is False
        assert "보안 검증 실패" in result.error
        
        # 실패 메트릭이 증가했는지 확인
        metrics = mock_apple_tool.get_performance_metrics()
        assert metrics["failed_requests"] == 1
        assert metrics["total_requests"] == 1

    def test_run_successful_operation(self, mock_apple_tool):
        """성공적인 작업 실행 테스트."""
        result = mock_apple_tool.run(
            app="notes",
            operation="search",
            query="test"
        )
        
        assert result.success is True
        assert result.data is not None
        
        # 성공 메트릭이 증가했는지 확인
        metrics = mock_apple_tool.get_performance_metrics()
        assert metrics["successful_requests"] == 1
        assert metrics["total_requests"] == 1
        assert metrics["success_rate"] == 1.0

    def test_batch_execution(self, mock_apple_tool):
        """배치 처리 테스트."""
        tasks = [
            {"app": "notes", "operation": "search", "query": "test1"},
            {"app": "contacts", "operation": "search", "query": "test2"},
            {"app": "notes", "operation": "create", "data": {"title": "test", "content": "body"}}
        ]
        
        results = mock_apple_tool.execute_batch(tasks)
        
        assert len(results) == 3
        for result in results:
            # ToolResult 타입 확인
            assert hasattr(result, 'success')
            assert hasattr(result, 'data')
            assert hasattr(result, 'error')
            assert result.success is True  # Mock이므로 모두 성공

    def test_timeout_configuration(self, mock_apple_tool):
        """타임아웃 설정 테스트."""
        custom_timeouts = {
            "notes": 15.0,
            "contacts": 20.0
        }
        
        mock_apple_tool.configure_timeouts(custom_timeouts)
        
        assert mock_apple_tool._app_timeouts["notes"] == 15.0
        assert mock_apple_tool._app_timeouts["contacts"] == 20.0

    def test_security_configuration(self, mock_apple_tool):
        """보안 설정 테스트."""
        mock_apple_tool.configure_security(
            max_text_length=5000,
            additional_patterns=["custom_dangerous_pattern"]
        )
        
        assert mock_apple_tool._max_text_length == 5000
        assert "custom_dangerous_pattern" in mock_apple_tool._dangerous_patterns

    def test_non_retryable_error_detection(self, mock_apple_tool):
        """재시도 불가능한 오류 감지 테스트."""
        permission_error = Exception("Permission denied")
        assert mock_apple_tool._is_non_retryable_error(permission_error) is True
        
        connection_error = Exception("Connection refused")
        assert mock_apple_tool._is_non_retryable_error(connection_error) is False

    def test_metrics_reset(self, mock_apple_tool):
        """메트릭 리셋 테스트."""
        # 먼저 몇 개의 작업 실행
        mock_apple_tool.run(app="notes", operation="search", query="test")

        # 메트릭 확인
        metrics_before = mock_apple_tool.get_performance_metrics()
        assert metrics_before["total_requests"] > 0

        # 리셋
        mock_apple_tool.reset_metrics()

        # 리셋 후 확인
        metrics_after = mock_apple_tool.get_performance_metrics()
        assert metrics_after["total_requests"] == 0
        assert metrics_after["successful_requests"] == 0

    def test_inspect_configuration_defaults(self, mock_apple_tool):
        """기본 설정 요약 확인."""
        config = mock_apple_tool.inspect_configuration()
        assert "app_timeouts" in config
        assert "notes" in config["app_timeouts"]
        assert config["max_retries"] == 2
        assert config["max_text_length"] == 10000
        assert any("shell" in pattern for pattern in config["dangerous_patterns"])

    def test_custom_initial_configuration(self, tmp_path):
        """초기화 시 커스텀 설정 적용 여부 확인."""
        external_dir = tmp_path / "external" / "apple-mcp"
        external_dir.mkdir(parents=True)
        import json
        with open(external_dir / "package.json", "w") as f:
            json.dump({"name": "apple-mcp", "scripts": {"start": "node index.js"}}, f)

        with patch('platform.system', return_value='Darwin'):
            tool = AppleTool(
                project_root=tmp_path,
                app_timeouts={"notes": 12.0},
                operation_timeouts={"notes.search": 22.0},
                security_patterns=["custom"],
                max_text_length=5000,
                max_retries=5,
            )

        config = tool.inspect_configuration()
        assert config["app_timeouts"]["notes"] == 12.0
        assert config["operation_timeouts"]["notes.search"] == 22.0
        assert config["max_text_length"] == 5000
        assert "custom" in config["dangerous_patterns"]
        assert config["max_retries"] == 5

    def test_performance_metrics_dataclass(self):
        """PerformanceMetrics 데이터클래스 테스트."""
        metrics = PerformanceMetrics()
        
        # 초기값 확인
        assert metrics.success_rate() == 0.0
        assert metrics.average_duration() == 0.0
        
        # 값 설정 후 계산 확인
        metrics.total_requests = 10
        metrics.successful_requests = 8
        metrics.total_duration = 20.0
        
        assert metrics.success_rate() == 0.8
        assert metrics.average_duration() == 2.5

    def test_parameter_validation(self, mock_apple_tool):
        """파라미터 검증 테스트."""
        # 잘못된 앱
        result = mock_apple_tool.run(app="invalid_app", operation="search")
        assert result.success is False
        assert "app 파라미터는 다음 중 하나여야 합니다" in result.error
        
        # 잘못된 작업
        result = mock_apple_tool.run(app="notes", operation="invalid_operation")
        assert result.success is False
        assert "에서 지원하는 operation" in result.error

    def test_macos_environment_check(self, tmp_path):
        """macOS 환경 체크 테스트."""
        with patch('platform.system', return_value='Windows'):
            with pytest.raises(Exception) as exc_info:
                AppleTool(project_root=tmp_path)
            assert "macOS에서만 사용할 수 있습니다" in str(exc_info.value)

    def test_server_running_check(self, mock_apple_tool):
        """서버 실행 상태 체크 테스트."""
        # 서버가 실행 중인 경우
        mock_apple_tool._manager.is_server_running.return_value = True
        assert mock_apple_tool._ensure_server_running() is True
        
        # 서버가 실행 중이지 않지만 시작 성공
        mock_apple_tool._manager.is_server_running.return_value = False
        mock_apple_tool._manager.start_server.return_value = True
        assert mock_apple_tool._ensure_server_running() is True
        
        # 서버 시작 실패
        mock_apple_tool._manager.start_server.return_value = False
        assert mock_apple_tool._ensure_server_running() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
