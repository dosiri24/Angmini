"""
CLI (Command Line Interface) 인터페이스
터미널에서 사용자와 AI Assistant가 대화할 수 있는 인터페이스를 제공합니다.
"""
from ai.core.logger import logger

class CLIInterface:
    """
    간단한 명령줄 인터페이스를 제공하는 클래스입니다.
    사용자의 입력을 받아 AI에게 전달하고, 응답을 출력하는 역할을 합니다.
    """
    
    def __init__(self):
        """CLI 인터페이스를 초기화합니다."""
        self.running = False
        logger.info("CLI 인터페이스가 초기화되었습니다.")
    
    def start(self):
        """
        CLI 인터페이스를 시작합니다.
        사용자가 'quit', 'exit', 'q' 중 하나를 입력할 때까지 계속 실행됩니다.
        """
        self.running = True
        logger.info("CLI 인터페이스를 시작합니다.")
        
        print("🤖 Personal AI Assistant CLI")
        print("도움이 필요하시면 무엇이든 말씀해주세요!")
        print("종료하려면 'quit', 'exit', 또는 'q'를 입력하세요.\n")
        
        while self.running:
            try:
                # 사용자 입력 받기
                user_input = input("사용자: ").strip()
                
                # 종료 명령어 확인
                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.stop()
                    break
                
                # 빈 입력 처리
                if not user_input:
                    continue
                
                # TODO: 여기에 AI 엔진 연동 로직 추가
                # 현재는 간단한 응답만 제공
                response = self._process_input(user_input)
                print(f"AI: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\n프로그램을 종료합니다.")
                self.stop()
                break
            except Exception as e:
                logger.error(f"CLI에서 오류가 발생했습니다: {e}")
                print("죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.\n")
    
    def stop(self):
        """CLI 인터페이스를 종료합니다."""
        self.running = False
        logger.info("CLI 인터페이스를 종료합니다.")
        print("안녕히 가세요! 👋")
    
    def _process_input(self, user_input: str) -> str:
        """
        사용자의 입력을 처리하고 응답을 생성합니다.
        현재는 간단한 더미 응답을 제공하며, 나중에 AI 엔진과 연동될 예정입니다.
        
        Args:
            user_input (str): 사용자가 입력한 텍스트
            
        Returns:
            str: AI의 응답 텍스트
        """
        logger.info(f"사용자 입력 처리: {user_input}")
        
        # TODO: Phase 2에서 ReAct Engine과 연동
        # 현재는 간단한 더미 응답 제공
        if "안녕" in user_input or "hello" in user_input.lower():
            return "안녕하세요! 저는 당신의 개인 AI 비서입니다. 어떻게 도와드릴까요?"
        elif "도움" in user_input or "help" in user_input.lower():
            return "저는 다양한 작업을 도와드릴 수 있습니다. 파일 관리, 정보 검색, 일정 관리 등 무엇이든 말씀해주세요!"
        elif "이름" in user_input or "name" in user_input.lower():
            return "저는 Angmini입니다! 당신의 개인 AI 비서로 열심히 도와드리겠습니다."
        else:
            return f"'{user_input}'에 대해 말씀해주셨군요. 현재는 기본 기능만 제공하고 있지만, 곧 더 똑똑해질 예정입니다!"

def run_cli():
    """CLI 인터페이스를 실행하는 함수입니다."""
    cli = CLIInterface()
    cli.start()

if __name__ == "__main__":
    run_cli()
