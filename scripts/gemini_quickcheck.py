"""Standalone Gemini API smoke test.

Usage
-----
    python scripts/gemini_quickcheck.py "질문 내용"

Reads `GEMINI_API_KEY` (필수)와 `GEMINI_MODEL` (선택, 기본값 gemini-1.5-pro)
from the current environment. If `.env` exists, it will be loaded automatically
when `python-dotenv`가 설치되어 있을 때.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

try:  # noqa: F401 - optional dependency for convenience
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None
else:  # pragma: no cover
    load_dotenv()


def mask(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-4:]}"


def normalise_model(raw: Optional[str]) -> str:
    model = (raw or "gemini-1.5-pro").strip()
    if model.startswith("models/"):
        model = model.split("/", 1)[1]
    return model


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY 환경변수가 비었습니다.", file=sys.stderr)
        raise SystemExit(1)

    model_name = normalise_model(os.getenv("GEMINI_MODEL"))

    try:
        import google.generativeai as genai
    except ImportError as exc:  # pragma: no cover
        print("google-generativeai 패키지를 찾을 수 없습니다.", file=sys.stderr)
        raise SystemExit(1) from exc

    prompt = "안녕?" if len(sys.argv) == 1 else " ".join(sys.argv[1:])

    print(f"Using model='{model_name}', api_key='{mask(api_key)}'")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    try:
        response = model.generate_content(prompt)
    except Exception as exc:  # pragma: no cover
        print("Gemini 요청 실패:", exc, file=sys.stderr)
        raise SystemExit(1)

    text = getattr(response, "text", None)
    if not text:
        print("응답에서 텍스트를 찾지 못했습니다.")
    else:
        print("--- 응답 시작 ---")
        print(text)
        print("--- 응답 끝 ---")


if __name__ == "__main__":
    main()
