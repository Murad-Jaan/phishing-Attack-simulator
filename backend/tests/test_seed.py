import subprocess
import os
import sys
from pathlib import Path


def test_seed_refuses_in_production():
    env = os.environ.copy()
    env['APP_ENV'] = 'production'
    backend_dir = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, '-m', 'app.scripts.seed_dev'],
        cwd=str(backend_dir),
        env=env,
        capture_output=True,
        text=True
    )
    assert result.returncode != 0
    assert 'production' in result.stderr.lower() or 'production' in result.stdout.lower()
