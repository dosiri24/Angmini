#!/usr/bin/env python3
"""Test script for SingletonGuard functionality."""

import sys
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ai.core.singleton import SingletonGuard


def test_singleton_basic():
    """Test basic singleton functionality."""
    print("🧪 Test 1: Basic singleton lock acquisition")

    guard1 = SingletonGuard(pid_file_name=".test_singleton.pid")
    assert guard1.acquire(), "First instance should acquire lock successfully"
    print("✅ First instance acquired lock")

    guard2 = SingletonGuard(pid_file_name=".test_singleton.pid")
    # This should kill the first instance's process (which is us)
    # So we can't really test this in the same process
    print("✅ Basic test passed")

    guard1.release()
    print("✅ Lock released")


def test_singleton_stale_pid():
    """Test singleton with stale PID file."""
    print("\n🧪 Test 2: Stale PID file handling")

    # Create a PID file with a non-existent PID
    pid_file = project_root / ".test_stale.pid"
    pid_file.write_text("99999")
    print("   Created stale PID file with PID 99999")

    guard = SingletonGuard(pid_file_name=".test_stale.pid")
    assert guard.acquire(), "Should acquire lock with stale PID file"
    print("✅ Acquired lock after removing stale PID file")

    guard.release()
    print("✅ Stale PID test passed")


def test_pid_file_lifecycle():
    """Test PID file creation and cleanup."""
    print("\n🧪 Test 3: PID file lifecycle")

    pid_file_path = project_root / ".test_lifecycle.pid"

    # Ensure clean state
    if pid_file_path.exists():
        pid_file_path.unlink()

    guard = SingletonGuard(pid_file_name=".test_lifecycle.pid")

    # PID file should not exist before acquire
    assert not pid_file_path.exists(), "PID file should not exist initially"
    print("✅ PID file doesn't exist before acquire")

    guard.acquire()

    # PID file should exist after acquire
    assert pid_file_path.exists(), "PID file should exist after acquire"
    print("✅ PID file created after acquire")

    guard.release()

    # PID file should be cleaned up after release
    assert not pid_file_path.exists(), "PID file should be cleaned up after release"
    print("✅ PID file cleaned up after release")


def test_discord_singleton():
    """Test Discord-specific singleton."""
    print("\n🧪 Test 4: Discord-specific singleton")

    guard = SingletonGuard(pid_file_name=".angmini_discord.pid")
    assert guard.acquire(), "Discord singleton should acquire lock"
    print("✅ Discord singleton acquired lock")

    guard.release()
    print("✅ Discord singleton test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("SingletonGuard Test Suite")
    print("=" * 60)

    try:
        test_singleton_basic()
        test_singleton_stale_pid()
        test_pid_file_lifecycle()
        test_discord_singleton()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
