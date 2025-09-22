"""Apple MCP 메모 생성 테스트."""

import json
import subprocess
import sys
import uuid
from pathlib import Path

def create_test_note():
    """테스트용 메모를 생성합니다."""
    
    # Apple MCP 경로
    apple_mcp_path = Path(__file__).parent.parent / "external" / "apple-mcp"
    
    # 고유한 테스트 메모 생성
    test_id = uuid.uuid4().hex[:8]
    note_title = f"테스트 메모 {test_id}"
    note_body = f"이것은 AppleTool 테스트용으로 자동 생성된 메모입니다.\n생성 시간: {test_id}\n\n삭제하셔도 됩니다."
    
    # 메모 생성 요청
    create_request = {
        "jsonrpc": "2.0",
        "id": "create_test",
        "method": "tools/call",
        "params": {
            "name": "notes",
            "arguments": {
                "operation": "create",
                "title": note_title,
                "body": note_body,
                "folderName": "AppleTool 테스트"
            }
        }
    }
    
    print(f"📝 테스트 메모 생성 시도")
    print(f"   제목: {note_title}")
    print(f"   내용: {note_body[:50]}...")
    print(f"   폴더: AppleTool 테스트")
    
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
        
        # 요청 전송 (더 긴 타임아웃)
        request_str = json.dumps(create_request) + "\n"
        stdout, stderr = process.communicate(input=request_str, timeout=30)
        
        print(f"\n📥 Apple MCP 서버 응답:")
        
        # 응답 파싱
        lines = stdout.strip().split('\n')
        json_response = None
        
        for line in lines:
            if line.startswith('{"'):
                try:
                    json_response = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        
        if json_response:
            print(f"✅ 응답 받음: {json.dumps(json_response, indent=2, ensure_ascii=False)}")
            
            # 성공 여부 확인
            if "result" in json_response:
                result = json_response["result"]
                if "content" in result:
                    content = result["content"]
                    if isinstance(content, list) and len(content) > 0:
                        text_content = content[0].get("text", "")
                        if "success" in text_content.lower() or "created" in text_content.lower():
                            print(f"🎉 메모 생성 성공!")
                            return True
                        else:
                            print(f"📝 메모 생성 결과: {text_content}")
                            return True
                    else:
                        print(f"📝 메모 생성 완료: {content}")
                        return True
                else:
                    print(f"📝 메모 생성 결과: {result}")
                    return True
            elif "error" in json_response:
                error = json_response["error"]
                print(f"❌ 메모 생성 실패: {error}")
                return False
        else:
            print("❌ JSON 응답을 찾을 수 없습니다.")
            print("전체 출력:")
            for line in lines:
                print(f"   {line}")
            return False
            
        if stderr:
            print(f"\n⚠️ 에러 출력:")
            for line in stderr.strip().split('\n'):
                if line.strip() and not line.startswith('$'):
                    print(f"   {line}")
                    
    except subprocess.TimeoutExpired:
        print("⏰ 30초 타임아웃 발생 - 권한 대화상자가 나타났을 수 있습니다.")
        print("💡 다음을 확인해주세요:")
        print("   1. 시스템 환경설정 > 보안 및 개인 정보 보호")
        print("   2. 개인 정보 보호 탭 > 전체 디스크 접근 권한")
        print("   3. Terminal 또는 Python 앱에 체크박스 활성화")
        process.kill()
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def list_recent_notes():
    """최근 메모 목록을 조회합니다."""
    
    apple_mcp_path = Path(__file__).parent.parent / "external" / "apple-mcp"
    
    list_request = {
        "jsonrpc": "2.0",
        "id": "list_test",
        "method": "tools/call",
        "params": {
            "name": "notes",
            "arguments": {
                "operation": "list"
            }
        }
    }
    
    print(f"\n📋 최근 메모 목록 조회 시도")
    
    try:
        cmd = ["bun", "run", "start"]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=apple_mcp_path
        )
        
        request_str = json.dumps(list_request) + "\n"
        stdout, stderr = process.communicate(input=request_str, timeout=15)
        
        lines = stdout.strip().split('\n')
        for line in lines:
            if line.startswith('{"'):
                try:
                    response = json.loads(line)
                    if "result" in response:
                        print("📝 메모 목록:")
                        result = response["result"]
                        if "content" in result:
                            content = result["content"]
                            if isinstance(content, list) and len(content) > 0:
                                text_content = content[0].get("text", "")
                                # 메모 목록을 줄별로 표시
                                for i, note_line in enumerate(text_content.strip().split('\n')[:10]):
                                    if note_line.strip():
                                        print(f"   {i+1}. {note_line.strip()}")
                            else:
                                print(f"   {content}")
                        else:
                            print(f"   {result}")
                        return True
                    elif "error" in response:
                        print(f"❌ 목록 조회 실패: {response['error']}")
                        return False
                except json.JSONDecodeError:
                    continue
                    
    except subprocess.TimeoutExpired:
        print("⏰ 목록 조회 타임아웃")
        process.kill()
        return False
    except Exception as e:
        print(f"❌ 목록 조회 오류: {e}")
        return False

if __name__ == "__main__":
    print("🍎 Apple MCP 메모 생성 테스트")
    print("=" * 50)
    
    # 먼저 기존 메모 목록 확인
    print("1️⃣ 기존 메모 목록 확인")
    list_recent_notes()
    
    print("\n" + "=" * 50)
    
    # 새 메모 생성
    print("2️⃣ 새 메모 생성")
    success = create_test_note()
    
    if success:
        print("\n" + "=" * 50)
        print("3️⃣ 생성 후 메모 목록 재확인")
        list_recent_notes()
    
    print("\n🎉 테스트 완료!")
    if not success:
        print("\n💡 권한 설정이 필요할 수 있습니다:")
        print("   시스템 환경설정 > 보안 및 개인 정보 보호 > 개인 정보 보호")
        print("   → 전체 디스크 접근 권한 → Terminal 체크")
