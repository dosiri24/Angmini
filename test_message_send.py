#!/usr/bin/env python3
"""메시지 전송 기능 테스트"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp.tools.apple_tool import AppleTool

def test_message_send():
    """메시지 전송 테스트"""
    
    # 환경변수 설정
    os.environ['AI_ASSISTANT_NAME'] = 'Angmini'
    
    print("=== 메시지 전송 기능 테스트 ===")
    
    # Apple 툴 초기화
    try:
        apple_tool = AppleTool()
        print("✅ Apple 툴 초기화 성공")
    except Exception as e:
        print(f"❌ Apple 툴 초기화 실패: {e}")
        return
    
    # 테스트 파라미터 (AI가 생성한 것과 동일한 구조)
    test_params = {
        'app': 'messages',
        'operation': 'send',
        'data': {
            'to': '01000000000',  # 테스트 번호
            'body': '테스트 메시지입니다'  # AI가 사용한 필드명
        }
    }
    
    print(f"입력 파라미터: {test_params}")
    
    # 파라미터 매핑 테스트
    try:
        mapped = apple_tool._map_parameters_for_app('messages', 'send', test_params)
        print(f"매핑된 파라미터: {mapped}")
        
        expected = {
            'operation': 'send',
            'phoneNumber': '01000000000',
            'message': '테스트 메시지입니다'
        }
        
        if mapped == expected:
            print("✅ 파라미터 매핑 성공")
        else:
            print(f"❌ 파라미터 매핑 실패. 예상: {expected}")
            return
            
    except Exception as e:
        print(f"❌ 파라미터 매핑 오류: {e}")
        return
    
    # 실제 메시지 전송 테스트 (주의: 실제 메시지가 전송될 수 있음)
    print("\n실제 메시지 전송을 테스트하시겠습니까? (y/N): ", end='')
    response = input().strip().lower()
    
    if response == 'y':
        try:
            result = apple_tool.run(**test_params)
            if result.success:
                print("✅ 메시지 전송 성공!")
                print(f"결과: {result.data}")
            else:
                print(f"❌ 메시지 전송 실패: {result.error}")
        except Exception as e:
            print(f"❌ 메시지 전송 중 오류: {e}")
    else:
        print("메시지 전송 테스트를 건너뜁니다.")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    test_message_send()
