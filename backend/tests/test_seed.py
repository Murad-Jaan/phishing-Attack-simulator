import subprocess
import os


def test_seed_refuses_in_production():
    env = os.environ.copy()
    env['APP_ENV'] = 'production'
    result = subprocess.run(
        ['python', '-m', 'app.scripts.seed_dev'],
        cwd='/app',
        env=env,
        capture_output=True,
        text=True
    )
    assert result.returncode != 0
    assert 'production' in result.stderr.lower() or 'production' in result.stdout.lower()
