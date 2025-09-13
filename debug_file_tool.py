#!/usr/bin/env python3
"""
FileTool 디버깅 테스트
"""

import sys
import os
sys.path.append('/Users/taesooa/Desktop/Python/Angmini/Angmini')

from mcp.tools.file_tool import FileTool
import json

def test_file_tool_debug():
    """FileTool 단독 테스트"""
    
    print("🔧 FileTool 디버깅 테스트")
    print("=" * 50)
    
    try:
        # FileTool 생성
        project_dir = "/Users/taesooa/Desktop/Python/Angmini/Angmini"
        file_tool = FileTool(allowed_base_paths=[project_dir])
        
        # 1. 간단한 읽기 테스트 (기존 파일)
        print("1. 기존 파일 읽기 테스트...")
        read_input = f'{{"action": "read", "path": "{project_dir}/README.md"}}'
        print(f"   입력: {read_input}")
        result = file_tool.execute_safe(read_input)
        print(f"   결과: {result.status.value}")
        print(f"   내용: {result.content[:100]}...")
        
        # 2. 디렉토리 목록 테스트
        print("\n2. 디렉토리 목록 테스트...")
        list_input = f'{{"action": "list", "path": "{project_dir}"}}'
        print(f"   입력: {list_input}")
        result = file_tool.execute_safe(list_input)
        print(f"   결과: {result.status.value}")
        print(f"   내용: {result.content[:200]}...")
        
        # 3. 파일 쓰기 테스트
        print("\n3. 파일 쓰기 테스트...")
        test_file = os.path.join(project_dir, "debug_test.txt")
        write_content = "디버그 테스트 내용"
        write_input = {
            "action": "write",
            "path": test_file,
            "content": write_content
        }
        write_input_str = json.dumps(write_input, ensure_ascii=False)
        print(f"   입력: {write_input_str}")
        result = file_tool.execute_safe(write_input_str)
        print(f"   결과: {result.status.value}")
        print(f"   내용: {result.content}")
        
        # 4. 생성된 파일 읽기 테스트
        if result.is_success():
            print("\n4. 생성된 파일 읽기 테스트...")
            read_input = json.dumps({"action": "read", "path": test_file}, ensure_ascii=False)
            print(f"   입력: {read_input}")
            result = file_tool.execute_safe(read_input)
            print(f"   결과: {result.status.value}")
            print(f"   내용: {result.content}")
            
            # 정리
            try:
                os.remove(test_file)
                print(f"   테스트 파일 정리 완료")
            except:
                print(f"   테스트 파일 정리 실패")
        
        print("\n" + "=" * 50)
        print("✅ FileTool 디버깅 완료!")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_file_tool_debug()
