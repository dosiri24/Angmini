"""Collection of built-in tools for the Personal AI Assistant."""

from __future__ import annotations

from .apple_tool import AppleTool  # noqa: F401
from .file_tool import FileTool  # noqa: F401
from .memory_tool import MemoryTool  # noqa: F401
from .notion_tool import NotionTool  # noqa: F401
from .image_analysis_tool import ImageAnalysisCrewAITool  # noqa: F401
from .document_analysis_tool import DocumentAnalysisCrewAITool  # noqa: F401
from .pdf_analysis_tool import PDFAnalysisCrewAITool  # noqa: F401

__all__ = [
    "AppleTool",
    "FileTool",
    "MemoryTool",
    "NotionTool",
    "ImageAnalysisCrewAITool",
    "DocumentAnalysisCrewAITool",
    "PDFAnalysisCrewAITool",
]
