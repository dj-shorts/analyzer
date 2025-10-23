"""
TestSprite Integration for pytest.

This file integrates TestSprite with the test suite.
"""

import os
from pathlib import Path

import pytest

# TestSprite configuration
TESTSPRITE_ENABLED = os.getenv("TESTSPRITE_ENABLED", "false").lower() == "true"
TESTSPRITE_API_KEY = os.getenv("TESTSPRITE_API_KEY")
TESTSPRITE_PROJECT = os.getenv("TESTSPRITE_PROJECT_ID", "dj-shorts-analyzer")

# Try to import TestSprite
testsprite_client = None
if TESTSPRITE_ENABLED:
    try:
        from testsprite import TestSprite

        if not TESTSPRITE_API_KEY:
            print("Warning: TESTSPRITE_ENABLED=true but TESTSPRITE_API_KEY not set")
        else:
            testsprite_client = TestSprite(
                api_key=TESTSPRITE_API_KEY,
                project=TESTSPRITE_PROJECT,
            )
            print(f"TestSprite enabled for project: {TESTSPRITE_PROJECT}")
    except ImportError:
        print("Warning: TestSprite SDK not installed")
        print("Install with: uv add testsprite")


@pytest.fixture(scope="session")
def testsprite():
    """Provide TestSprite client to tests."""
    return testsprite_client


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to report test results to TestSprite."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and testsprite_client:
        # Extract test metadata
        tags = []
        priority = "normal"
        requirements = []

        # Get markers
        for marker in item.iter_markers():
            if marker.name == "testsprite":
                tags = marker.kwargs.get("tags", [])
                priority = marker.kwargs.get("priority", "normal")
                requirements = marker.kwargs.get("requirements", [])
            else:
                # Add marker names as tags
                tags.append(marker.name)

        # Report to TestSprite
        try:
            testsprite_client.report_test(
                name=item.nodeid,
                status=report.outcome,  # passed/failed/skipped
                duration=report.duration,
                tags=tags,
                priority=priority,
                requirements=requirements,
                error=str(report.longrepr) if report.failed else None,
                stdout=report.capstdout if hasattr(report, "capstdout") else None,
                stderr=report.capstderr if hasattr(report, "capstderr") else None,
            )
        except Exception as e:
            print(f"Failed to report test to TestSprite: {e}")


def pytest_collection_finish(session):
    """Hook called after test collection is finished."""
    if testsprite_client:
        print(f"\nCollected {len(session.items)} tests")
        print("TestSprite reporting enabled")


def pytest_sessionfinish(session, exitstatus):
    """Hook called after whole test run finished."""
    if testsprite_client:
        try:
            # Upload session summary
            testsprite_client.finish_session(
                total=session.testscollected,
                passed=session.testscollected - session.testsfailed,
                failed=session.testsfailed,
                exit_status=exitstatus,
            )
            print("\nTest results uploaded to TestSprite")
        except Exception as e:
            print(f"\nFailed to finalize TestSprite session: {e}")


# Custom pytest markers for TestSprite
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "testsprite: TestSprite metadata (tags, priority, requirements)"
    )
    config.addinivalue_line("markers", "unit: Unit test")
    config.addinivalue_line("markers", "integration: Integration test")
    config.addinivalue_line("markers", "performance: Performance test")
    config.addinivalue_line("markers", "regression: Regression test")
    config.addinivalue_line("markers", "slow: Slow test (> 5s)")
    config.addinivalue_line("markers", "requires_ffmpeg: Requires ffmpeg")
    config.addinivalue_line("markers", "requires_video: Requires video file")
