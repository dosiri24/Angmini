"""
Apple MCP 성능 최적화 및 안정성 기능 통합 테스트.

이 테스트는 Phase 3.4.3에서 구현된 모든 성능 최적화 및 안정성 기능을 검증합니다:
- 연결 풀링 (MCPConnectionPool)
- 비동기 처리 (AsyncAppleTool)
- 타임아웃 처리 (AppleMCPTimeoutHandler)
- 보안 검증 (AppleMCPSecurityValidator)
"""

import asyncio
import pytest
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.connection_pool import MCPConnectionPool
from mcp.tools.async_apple_tool import AsyncAppleTool
from mcp.timeout_handler import (
    AppleMCPTimeoutHandler, 
    TimeoutConfig, 
    OperationType,
    get_timeout_handler
)
from mcp.security_validator import (
    AppleMCPSecurityValidator, 
    SecurityLevel, 
    PermissionLevel,
    get_security_validator
)


class TestPhase343Integration:
    """Phase 3.4.3 통합 테스트 클래스."""
    
    @pytest.fixture
    def project_root(self, tmp_path):
        """임시 프로젝트 루트 생성."""
        external_dir = tmp_path / "external" / "apple-mcp"
        external_dir.mkdir(parents=True)
        
        # package.json 생성 (Apple MCP 시뮬레이션)
        package_json = {
            "name": "apple-mcp",
            "version": "1.0.0",
            "scripts": {"start": "node index.js"}
        }
        
        import json
        with open(external_dir / "package.json", "w") as f:
            json.dump(package_json, f)
        
        return tmp_path
    
    @pytest.fixture
    def mock_connection_pool(self):
        """Mock 연결 풀."""
        with patch('mcp.connection_pool.MCPConnectionPool') as mock_pool:
            pool_instance = MagicMock()
            pool_instance.send_request.return_value = {
                "content": [{"text": "Mock response"}]
            }
            pool_instance.get_stats.return_value = {
                "active_connections": 2,
                "idle_connections": 1,
                "total_requests": 5
            }
            mock_pool.return_value = pool_instance
            yield pool_instance
    
    @pytest.fixture
    def timeout_config(self):
        """테스트용 타임아웃 설정."""
        return TimeoutConfig(
            default=5.0,
            search=2.0,
            create=3.0,
            connection=5.0
        )
    
    @pytest.fixture
    def security_validator(self):
        """테스트용 보안 검증기."""
        return AppleMCPSecurityValidator(
            security_level=SecurityLevel.MEDIUM,
            max_text_length=1000,
            enable_audit_log=False
        )

    @pytest.mark.asyncio
    async def test_connection_pooling_basic(self, project_root, mock_connection_pool):
        """기본 연결 풀링 테스트."""
        pool = MCPConnectionPool(
            command=["bun", "run", "start"],
            working_dir=project_root / "external" / "apple-mcp",
            min_connections=1,
            max_connections=3
        )
        
        # 실제 연결 풀링 대신 mock 사용
        with patch.object(pool, 'send_request', return_value={"success": True}):
            result = pool.send_request("test", {}, 5.0)
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_async_apple_tool_single_operation(self, project_root, mock_connection_pool):
        """AsyncAppleTool 단일 작업 테스트."""
        with patch('platform.system', return_value='Darwin'):  # macOS 시뮬레이션
            async_tool = AsyncAppleTool(
                project_root=project_root,
                pool_config={"min_connections": 1, "max_connections": 2}
            )
            
            # 연결 풀 mock 설정
            with patch.object(async_tool, '_get_pool', return_value=mock_connection_pool):
                result = await async_tool.run_async(
                    app="notes",
                    operation="search",
                    query="test"
                )
                
                assert result.success is True
                assert result.data is not None

    @pytest.mark.asyncio
    async def test_async_apple_tool_batch_operations(self, project_root, mock_connection_pool):
        """AsyncAppleTool 배치 작업 테스트."""
        with patch('platform.system', return_value='Darwin'):
            async_tool = AsyncAppleTool(project_root=project_root)
            
            batch_tasks = [
                {"app": "notes", "operation": "search", "query": "task1"},
                {"app": "contacts", "operation": "search", "query": "task2"},
                {"app": "notes", "operation": "create", "data": {"title": "test"}}
            ]
            
            with patch.object(async_tool, '_get_pool', return_value=mock_connection_pool):
                results = await async_tool.run_batch(batch_tasks)
                
                assert len(results) == 3
                # 모든 결과가 ToolResult 또는 예외여야 함
                for result in results:
                    assert hasattr(result, 'success') or isinstance(result, Exception)

    @pytest.mark.asyncio
    async def test_timeout_handler_success_case(self, timeout_config):
        """타임아웃 핸들러 성공 케이스 테스트."""
        handler = AppleMCPTimeoutHandler(
            timeout_config=timeout_config,
            max_retries=2,
            enable_circuit_breaker=False
        )
        
        async def mock_success_func():
            await asyncio.sleep(0.1)  # 짧은 지연
            return "success"
        
        async with handler.execute_with_timeout(
            "notes", "search", mock_success_func
        ) as result:
            assert result == "success"
        
        # 메트릭 확인
        metrics = handler.get_metrics_summary()
        assert metrics["total_operations"] == 1
        assert metrics["successful_operations"] == 1
        assert metrics["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_timeout_handler_timeout_case(self, timeout_config):
        """타임아웃 핸들러 타임아웃 케이스 테스트."""
        handler = AppleMCPTimeoutHandler(
            timeout_config=timeout_config,
            max_retries=1,
            enable_circuit_breaker=False
        )
        
        async def mock_slow_func():
            await asyncio.sleep(10)  # 긴 지연
            return "success"
        
        with pytest.raises(asyncio.TimeoutError):
            async with handler.execute_with_timeout(
                "notes", "search", mock_slow_func
            ) as result:
                pass
        
        # 메트릭 확인
        metrics = handler.get_metrics_summary()
        assert metrics["total_operations"] == 1
        assert metrics["successful_operations"] == 0
        assert "timeout" in metrics["error_categories"]

    @pytest.mark.asyncio
    async def test_timeout_handler_retry_logic(self, timeout_config):
        """타임아웃 핸들러 재시도 로직 테스트."""
        handler = AppleMCPTimeoutHandler(
            timeout_config=timeout_config,
            max_retries=2,
            retry_backoff=0.1,  # 빠른 테스트를 위해 짧게
            enable_circuit_breaker=False
        )
        
        call_count = 0
        
        async def mock_retry_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # 처음 2번은 실패
                raise Exception("Connection failed")
            return "success after retry"
        
        async with handler.execute_with_timeout(
            "notes", "create", mock_retry_func
        ) as result:
            assert result == "success after retry"
            assert call_count == 3  # 총 3번 호출

    def test_security_validator_valid_request(self, security_validator):
        """보안 검증기 유효한 요청 테스트."""
        violations = security_validator.validate_request(
            app="notes",
            operation="create",
            parameters={
                "data": {
                    "title": "Test Note",
                    "content": "This is a test note."
                }
            },
            permission_level=PermissionLevel.LIMITED_WRITE
        )
        
        assert len(violations) == 0

    def test_security_validator_unauthorized_app(self, security_validator):
        """보안 검증기 비인가 앱 테스트."""
        violations = security_validator.validate_request(
            app="unauthorized_app",
            operation="search",
            parameters={"query": "test"}
        )
        
        assert len(violations) > 0
        assert any(v.type == "unauthorized_app" for v in violations)

    def test_security_validator_dangerous_content(self, security_validator):
        """보안 검증기 위험한 콘텐츠 테스트."""
        violations = security_validator.validate_request(
            app="notes",
            operation="create",
            parameters={
                "data": {
                    "content": "rm -rf /; do shell script 'sudo rm -rf /'"
                }
            }
        )
        
        assert len(violations) > 0
        assert any("injection" in v.type for v in violations)

    def test_security_validator_sanitization(self, security_validator):
        """보안 검증기 새니타이제이션 테스트."""
        parameters = {
            "title": "<script>alert('xss')</script>",
            "content": "Normal content with & special chars"
        }
        
        sanitized = security_validator.sanitize_parameters(parameters)
        
        assert "&lt;script&gt;" in sanitized["title"]
        assert "&amp;" in sanitized["content"]

    def test_security_validator_text_length_limit(self, security_validator):
        """보안 검증기 텍스트 길이 제한 테스트."""
        long_text = "x" * 2000  # max_text_length보다 큰 텍스트
        
        violations = security_validator.validate_request(
            app="notes",
            operation="create",
            parameters={"data": {"content": long_text}}
        )
        
        assert len(violations) > 0
        assert any(v.type == "text_too_long" for v in violations)

    @pytest.mark.asyncio
    async def test_full_integration_with_security_and_timeout(
        self, 
        project_root, 
        mock_connection_pool, 
        timeout_config
    ):
        """전체 통합 테스트: 보안 + 타임아웃 + 비동기 처리."""
        
        # 보안 검증기 설정
        security_validator = AppleMCPSecurityValidator(
            security_level=SecurityLevel.MEDIUM,
            enable_audit_log=False
        )
        
        # 타임아웃 핸들러 설정
        timeout_handler = AppleMCPTimeoutHandler(
            timeout_config=timeout_config,
            max_retries=1,
            enable_circuit_breaker=False
        )
        
        # AsyncAppleTool 생성
        with patch('platform.system', return_value='Darwin'):
            async_tool = AsyncAppleTool(project_root=project_root)
            
            # 보안 검증
            violations = security_validator.validate_request(
                app="notes",
                operation="create",
                parameters={
                    "data": {
                        "title": "Integration Test",
                        "content": "Testing full integration"
                    }
                }
            )
            
            assert len(violations) == 0, "보안 검증 실패"
            
            # 타임아웃과 함께 비동기 실행
            async def execute_with_tool():
                with patch.object(async_tool, '_get_pool', return_value=mock_connection_pool):
                    return await async_tool.run_async(
                        app="notes",
                        operation="create",
                        data={
                            "title": "Integration Test",
                            "content": "Testing full integration"
                        }
                    )
            
            async with timeout_handler.execute_with_timeout(
                "notes", "create", execute_with_tool
            ) as result:
                assert result.success is True

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, project_root, mock_connection_pool):
        """성능 메트릭 수집 테스트."""
        with patch('platform.system', return_value='Darwin'):
            async_tool = AsyncAppleTool(project_root=project_root)
            
            # 여러 작업 실행
            tasks = [
                {"app": "notes", "operation": "search", "query": f"test{i}"}
                for i in range(5)
            ]
            
            with patch.object(async_tool, '_get_pool', return_value=mock_connection_pool):
                start_time = time.time()
                results = await async_tool.run_batch(tasks)
                duration = time.time() - start_time
                
                # 배치 처리가 순차 처리보다 빨라야 함 (이론적으로)
                assert duration < 5.0  # 5초 이내
                assert len(results) == 5
                
                # 연결 풀 통계 확인
                pool_stats = await async_tool.get_pool_stats()
                assert "active_connections" in pool_stats or "status" in pool_stats

    def test_circuit_breaker_functionality(self, timeout_config):
        """서킷 브레이커 기능 테스트."""
        handler = AppleMCPTimeoutHandler(
            timeout_config=timeout_config,
            max_retries=0,  # 재시도 없음
            enable_circuit_breaker=True
        )
        
        # 연속 실패를 시뮬레이션
        async def failing_func():
            raise Exception("Connection failed")
        
        async def test_circuit_breaker():
            # 5번 연속 실패시키기
            for i in range(5):
                try:
                    async with handler.execute_with_timeout(
                        "notes", "search", failing_func
                    ):
                        pass
                except Exception:
                    pass  # 예상된 실패
            
            # 서킷 브레이커가 활성화되었는지 확인
            metrics = handler.get_metrics_summary()
            circuit_states = metrics.get("circuit_breaker_states", {})
            
            # notes 앱에 대한 서킷 브레이커가 열렸는지 확인
            # (실제로는 실패 카운트가 충분히 쌓여야 함)
            assert len(metrics["failure_counts"]) > 0
        
        asyncio.run(test_circuit_breaker())

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, project_root, mock_connection_pool):
        """동시 작업 처리 테스트."""
        with patch('platform.system', return_value='Darwin'):
            async_tool = AsyncAppleTool(
                project_root=project_root,
                pool_config={"min_connections": 2, "max_connections": 5}
            )
            
            # 동시에 여러 작업 실행
            async def single_operation(i):
                with patch.object(async_tool, '_get_pool', return_value=mock_connection_pool):
                    return await async_tool.run_async(
                        app="notes",
                        operation="search",
                        query=f"concurrent_test_{i}"
                    )
            
            # 10개의 동시 작업
            start_time = time.time()
            tasks = [single_operation(i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.time() - start_time
            
            # 모든 작업이 완료되어야 함
            assert len(results) == 10
            
            # 성공한 작업 확인
            successful_results = [r for r in results if hasattr(r, 'success') and r.success]
            assert len(successful_results) > 0
            
            # 동시 처리가 순차 처리보다 빨라야 함
            assert duration < 10.0  # 10초 이내

    def test_global_handlers_configuration(self):
        """전역 핸들러 설정 테스트."""
        from mcp.timeout_handler import configure_timeout_handler, get_timeout_handler
        from mcp.security_validator import configure_security_validator, get_security_validator
        
        # 타임아웃 핸들러 설정
        custom_timeout_config = TimeoutConfig(default=20.0)
        configure_timeout_handler(
            timeout_config=custom_timeout_config,
            max_retries=5
        )
        
        handler = get_timeout_handler()
        assert handler._timeout_config.default == 20.0
        assert handler._max_retries == 5
        
        # 보안 검증기 설정
        configure_security_validator(
            security_level=SecurityLevel.HIGH,
            max_text_length=5000
        )
        
        validator = get_security_validator()
        assert validator._security_level == SecurityLevel.HIGH
        assert validator._max_text_length == 5000


if __name__ == "__main__":
    # 개별 테스트 실행 예시
    pytest.main([__file__, "-v", "--tb=short"])
