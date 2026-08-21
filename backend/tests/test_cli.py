from __future__ import annotations

import pytest

from ontoforge.cli import DEFAULT_HOST, DEFAULT_PORT, build_parser, main


def test_serve_binds_loopback_by_default() -> None:
    arguments = build_parser().parse_args(["serve"])
    assert (arguments.host, arguments.port) == (DEFAULT_HOST, DEFAULT_PORT)


def test_serve_accepts_an_explicit_host_and_port() -> None:
    arguments = build_parser().parse_args(["serve", "--host", "0.0.0.0", "--port", "9000"])
    assert (arguments.host, arguments.port) == ("0.0.0.0", 9000)


def test_a_command_is_required() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_info_prints_the_configuration_without_leaking_the_token(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("ONTOFORGE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ONTOFORGE_AUTH_TOKEN", "s3cret")
    assert main(["info"]) == 0
    output = capsys.readouterr().out
    assert "auth_token: <set>" in output
    assert "s3cret" not in output
