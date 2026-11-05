import os
import subprocess
import sys

import pytest

from tests.e2e_fixtures import ffmpeg_available


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")
@pytest.mark.skipif(not ffmpeg_available(), reason="needs ffmpeg on PATH")
def test_e2e_pipeline():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "-m", "tests.run_e2e_pipeline"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        timeout=900,
        env={**os.environ},
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    assert result.returncode == 0, f"E2E pipeline failed:\n{result.stdout}\n{result.stderr}"
