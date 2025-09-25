"""Diagnostics and logging helpers for AppleMCPManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from mcp.apple_mcp_manager import AppleMCPManager


def _prepare_minimal_mcp_tree(tmp_path: Path) -> None:
    apple_dir = tmp_path / "external" / "apple-mcp"
    (apple_dir / "dist").mkdir(parents=True)
    (apple_dir / "node_modules").mkdir()
    (apple_dir / "dist" / "index.js").write_text("console.log('stub');", encoding="utf-8")
    (apple_dir / "package.json").write_text("{}", encoding="utf-8")


def test_get_runtime_diagnostics(tmp_path):
    _prepare_minimal_mcp_tree(tmp_path)
    manager = AppleMCPManager(project_root=tmp_path)

    with patch.object(
        manager._installer,  # noqa: SLF001 - test helper
        "check_prerequisites",
        return_value={"bun": True, "macos": True, "apple_mcp_path": True},
    ):
        diag = manager.get_runtime_diagnostics()
    assert "installer" in diag
    assert diag["installer"]["installed"] is True
    assert "process_manager" in diag
    assert diag["process_manager"]["restart_count"] == 0


def test_get_status_structure(tmp_path):
    _prepare_minimal_mcp_tree(tmp_path)
    manager = AppleMCPManager(project_root=tmp_path)

    with patch.object(
        manager._installer,  # noqa: SLF001 - test helper
        "check_prerequisites",
        return_value={"bun": True, "macos": True, "apple_mcp_path": True},
    ):
        with patch.object(manager, "is_server_running", return_value=False):
            status = manager.get_status()

    assert "server_running" in status
    assert "restart" in status
    assert "can_restart" in status
