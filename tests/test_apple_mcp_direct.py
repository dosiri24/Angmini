"""간단한 Apple MCP 직접 테스트."""

import json
import subprocess
import sys
from pathlib import Path

def test_apple_mcp_direct():
    """Apple MCP를 직접 호출해서 메모 기능을 테스트합니다."""
    
    # Apple MCP 경로
    apple_mcp_path = Path(__file__).parent.parent / "external" / "apple-mcp"
    print(f"Apple MCP 경로: {apple_mcp_path}")
    
    # 테스트 요청들
    test_requests = [
        {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/list",
            "params": {}
        },
        {
            "jsonrpc": "2.0", 
            "id": "2",
            "method": "tools/call",
            "params": {
                "name": "notes",
                "arguments": {"operation": "list"}
            }
        },
        {
            "jsonrpc": "2.0",
            "id": "3", 
            "method": "tools/call",
            "params": {
                "name": "notes",
                "arguments": {
                    "operation": "search",
                    "searchText": "test"
                }
            }
        }
    ]
    
    for i, request in enumerate(test_requests):
        print(f"\n📤 테스트 {i+1}: {request['method']}")
        print(f"   파라미터: {request.get('params', {})}")
        
        try:
            # Apple MCP 서버 실행
            cmd = ["bun", "run", "start"]
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=apple_mcp_path
            )
            
            # 요청 전송
            request_str = json.dumps(request) + "\n"
            stdout, stderr = process.communicate(input=request_str, timeout=10)
            
            print(f"📥 응답:")
            # 서버 로그와 JSON 응답 분리
            lines = stdout.strip().split('\n')
            for line in lines:
                if line.startswith('{"'):
                    try:
                        response = json.loads(line)
                        print(f"   {json.dumps(response, indent=2, ensure_ascii=False)}")
                    except json.JSONDecodeError:
                        print(f"   (JSON 파싱 실패): {line}")
                else:
                    print(f"   (로그): {line}")
            
            if stderr:
                print(f"⚠️ 에러 출력: {stderr}")
                
        except subprocess.TimeoutExpired:
            print("⏰ 타임아웃 발생")
            process.kill()
        except Exception as e:
            print(f"❌ 오류: {e}")

if __name__ == "__main__":
    test_apple_mcp_direct()
