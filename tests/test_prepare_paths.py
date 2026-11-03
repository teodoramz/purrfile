"""The Action's pre-step: purrfile must be able to write next to files a Docker action (snk) created as root."""
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare-paths.sh"


def run(*paths):
    return subprocess.run(["bash", str(SCRIPT), *map(str, paths)], capture_output=True, text=True)


def test_creates_missing_folders(tmp_path):
    target = tmp_path / "dist" / "desktop.svg"
    result = run(target)
    assert result.returncode == 0
    assert os.access(target.parent, os.W_OK)


def test_makes_a_read_only_folder_and_its_files_writable(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    snake = dist / "github-snake.svg"
    snake.write_text("<svg/>")
    snake.chmod(0o444)
    dist.chmod(0o555)
    try:
        result = run(dist / "desktop.svg", snake)
        assert result.returncode == 0, result.stdout + result.stderr
        assert os.access(dist, os.W_OK)
        assert os.access(snake, os.W_OK)
    finally:
        dist.chmod(0o755)


def test_empty_arguments_are_ignored(tmp_path):
    assert run("", "").returncode == 0


@pytest.mark.skipif(not os.environ.get("PURRFILE_DOCKER_TESTS") or not shutil.which("docker"),
                    reason="set PURRFILE_DOCKER_TESTS=1 to run the root-owned folder check in Docker")
def test_root_owned_folder_like_snk_makes_it(tmp_path):
    """Reproduce the GitHub runner: root creates dist/, a sudo-capable normal user must then write into it."""
    repo = Path(__file__).resolve().parents[1]
    script = (
        "set -e; apt-get -qq update >/dev/null && apt-get -qq install -y sudo >/dev/null; "
        "useradd -m runner && echo 'runner ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/runner; "
        "mkdir -p /w/dist && cp /src/tests/fixtures/snk-dark.svg /w/dist/github-snake-dark.svg; "
        "chown -R root:root /w && chmod 755 /w/dist && chmod 777 /w; "
        "cd /w && su runner -c 'bash /src/scripts/prepare-paths.sh dist/desktop.svg dist/github-snake-dark.svg "
        "&& PYTHONPATH=/src/src python3 -m purrfile desktop /src/tests/fixtures/teodor-snapshot.json --output dist/desktop.svg "
        "&& PYTHONPATH=/src/src python3 -m purrfile hunt /src/tests/fixtures/teodor-snapshot.json dist/github-snake-dark.svg' "
        "&& grep -q about_me.txt dist/desktop.svg && grep -q purrfile-hunter dist/github-snake-dark.svg && echo OK"
    )
    result = subprocess.run(
        ["docker", "run", "--rm", "-e", "PYTHONDONTWRITEBYTECODE=1", "-v", f"{repo}:/src:ro", "python:3.10-slim",
         "bash", "-c", script],
        capture_output=True, text=True, timeout=600,
    )
    assert result.stdout.strip().endswith("OK"), result.stdout + result.stderr
