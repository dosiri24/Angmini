"""Notion 데이터베이스 필드명 확인 스크립트"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from mcp.tools.notion_tool import NotionTool

def main():
    load_dotenv()
    notion = NotionTool()

    # TODO 데이터베이스 ID
    db_id = os.getenv("NOTION_TODO_DATABASE_ID")
    if not db_id:
        print("ERROR: NOTION_TODO_DATABASE_ID not set")
        return

    print(f"Checking Notion TODO database: {db_id}\n")

    # 데이터베이스 정보 가져오기
    result = notion._call({
        "method": "get_database",
        "database_id": db_id
    })

    if result.error:
        print(f"ERROR: {result.error}")
        return

    # 필드 목록 출력
    properties = result.data.get("properties", {})
    print("=== Available Properties ===")
    for name, prop in properties.items():
        prop_type = prop.get("type", "unknown")
        print(f"  - {name:30s} ({prop_type})")

    print("\n=== Date Properties ===")
    for name, prop in properties.items():
        if prop.get("type") == "date":
            print(f"  - {name}")

if __name__ == "__main__":
    main()
