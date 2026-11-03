import json
import shutil

import pytest
from helpers import FIXTURES, teodor

import purrfile.collect
from purrfile.cli import load_extra_lines, main, write_atomic
from purrfile.collect import CollectError
from purrfile.hunt import MARKER
from purrfile.snapshot import snapshot_to_dict

FOREIGN = "<svg xmlns='http://www.w3.org/2000/svg'><rect width='1' height='1'/></svg>"


@pytest.fixture
def snap_file(tmp_path):
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot_to_dict(teodor())))
    return path


@pytest.fixture
def fake_collect(monkeypatch):
    monkeypatch.setattr(purrfile.collect, "fetch_snapshot", lambda login, token, today: teodor())


@pytest.fixture
def failing_collect(monkeypatch):
    def fail(login, token, today):
        raise CollectError("GitHub said no")

    monkeypatch.setattr(purrfile.collect, "fetch_snapshot", fail)


def snakes(tmp_path):
    dark, light = tmp_path / "github-snake-dark.svg", tmp_path / "github-snake.svg"
    shutil.copy(FIXTURES / "snk-dark.svg", dark)
    shutil.copy(FIXTURES / "snk-light.svg", light)
    return dark, light


def test_write_atomic(tmp_path):
    target = tmp_path / "a.svg"
    write_atomic(target, "one")
    write_atomic(target, "two")
    assert target.read_text() == "two"
    assert [p.name for p in tmp_path.iterdir()] == ["a.svg"]


def test_load_extra_lines(tmp_path, capsys):
    f = tmp_path / "lines.txt"
    f.write_text("# my lines\n\nI am a cat.\n  Meow.  \n")
    assert load_extra_lines(str(f)) == ["I am a cat.", "Meow."]
    assert load_extra_lines("") == []
    assert load_extra_lines(str(tmp_path / "missing.txt")) == []
    assert "::warning::" in capsys.readouterr().out


def test_desktop_command(tmp_path, snap_file):
    out = tmp_path / "desktop.svg"
    assert main(["desktop", str(snap_file), "--output", str(out), "--date", "2026-11-03"]) == 0
    assert "about_me.txt" in out.read_text()


def test_hunt_command(tmp_path, snap_file):
    dark, light = snakes(tmp_path)
    assert main(["hunt", str(snap_file), str(dark), str(light), "--date", "2026-11-03"]) == 0
    assert MARKER in dark.read_text() and MARKER in light.read_text()


def test_cli_hunt_failsafe(tmp_path, snap_file, fake_collect, capsys):
    foreign = tmp_path / "foreign.svg"
    foreign.write_text(FOREIGN)
    assert main(["hunt", str(snap_file), str(foreign)]) == 1
    assert foreign.read_text() == FOREIGN
    assert main(["run", "--login", "teodoramz", "--snake", str(foreign)]) == 0
    assert foreign.read_text() == FOREIGN
    assert "::warning::" in capsys.readouterr().out


def test_run_happy_path(tmp_path, fake_collect, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    dark, light = snakes(tmp_path)
    desktop = tmp_path / "desktop.svg"
    code = main(["run", "--login", "teodoramz", "--desktop", str(desktop), "--snake", f"{light} {dark}",
                 "--cat-name", "Mochi", "--extra-lines", "", "--date", "2026-11-03"])
    assert code == 0
    assert "about_me.txt" in desktop.read_text()
    assert MARKER in dark.read_text() and MARKER in light.read_text()


def test_run_twice_is_stable(tmp_path, fake_collect):
    dark, _ = snakes(tmp_path)
    args = ["run", "--login", "teodoramz", "--snake", str(dark), "--date", "2026-11-03"]
    main(args)
    once = dark.read_text()
    main(args)
    assert dark.read_text() == once


def test_run_collect_failure_keeps_files(tmp_path, failing_collect, capsys):
    dark, light = snakes(tmp_path)
    desktop = tmp_path / "desktop.svg"
    desktop.write_text("old desktop")
    before = dark.read_text(), light.read_text()
    code = main(["run", "--login", "teodoramz", "--desktop", str(desktop), "--snake", f"{dark} {light}"])
    assert code == 0
    assert desktop.read_text() == "old desktop"
    assert (dark.read_text(), light.read_text()) == before
    assert "::warning::" in capsys.readouterr().out


def test_run_with_empty_inputs_does_nothing(tmp_path, fake_collect):
    assert main(["run", "--login", "teodoramz", "--desktop", "", "--snake", ""]) == 0


def test_collect_command_errors_return_1(tmp_path, failing_collect, capsys):
    assert main(["collect", "teodoramz", "--output", str(tmp_path / "s.json")]) == 1
    assert not (tmp_path / "s.json").exists()
    assert "GitHub said no" in capsys.readouterr().err


def test_help(capsys):
    with pytest.raises(SystemExit) as exit_:
        main(["--help"])
    assert exit_.value.code == 0
    assert "run" in capsys.readouterr().out


def test_write_atomic_uses_normal_file_permissions(tmp_path):
    import os
    import stat

    old = os.umask(0o022)
    try:
        fresh = tmp_path / "fresh.svg"
        write_atomic(fresh, "x")
        assert stat.S_IMODE(fresh.stat().st_mode) == 0o644
        kept = tmp_path / "kept.svg"
        kept.write_text("old")
        kept.chmod(0o664)
        write_atomic(kept, "new")
        assert stat.S_IMODE(kept.stat().st_mode) == 0o664
    finally:
        os.umask(old)
