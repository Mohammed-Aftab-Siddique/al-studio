import sys

import pytest

from app.web import launcher


def test_choose_port_uses_first_available_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "available", lambda port: port == 8179)
    assert launcher.choose_port(None) == 8179


def test_choose_port_respects_explicit_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "available", lambda port: port == 9123)
    assert launcher.choose_port(9123) == 9123
    with pytest.raises(RuntimeError):
        launcher.choose_port(9124)


def test_launcher_binds_loopback_and_can_open_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_args = {}
    opened = []

    class ImmediateTimer:
        def __init__(self, _delay, callback, args):
            self.callback = callback
            self.args = args

        def start(self) -> None:
            self.callback(*self.args)

    monkeypatch.setattr(sys, "argv", ["al-studio-web", "--port", "9123"])
    monkeypatch.setattr(launcher, "choose_port", lambda requested: requested)
    monkeypatch.setattr(launcher.threading, "Timer", ImmediateTimer)
    monkeypatch.setattr(launcher.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(launcher.uvicorn, "run", lambda *args, **kwargs: run_args.update(kwargs))

    launcher.main()

    assert opened == ["http://127.0.0.1:9123"]
    assert run_args["host"] == "127.0.0.1"
    assert run_args["port"] == 9123
