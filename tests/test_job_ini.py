"""Verifica que el job serializa a INI parseable y correcto."""

from __future__ import annotations

import configparser
from pathlib import Path

from fb2p_studio.core.job import Job, Operation, OperationOptions


def test_job_serializes_to_valid_ini(tmp_path: Path) -> None:
    job = Job(
        foxbin2prg_home=r"D:\FoxBin2Prg",
        event_stream=tmp_path / "events.jsonl",
        operations=[
            Operation(
                id="op1",
                file=r"C:\proj\form.scx",
                type="BIN2PRG",
                options=OperationOptions(no_timestamps=1, debug=0, recompile=1),
            ),
        ],
        dry_run=False,
    )
    ini = job.to_ini()

    cp = configparser.ConfigParser(interpolation=None)
    cp.read_string(ini)

    assert cp["job"]["foxbin2prgHome"] == r"D:\FoxBin2Prg"
    assert cp["job"]["dryRun"] == "0"
    assert cp["op:op1"]["file"] == r"C:\proj\form.scx"
    assert cp["op:op1"]["type"] == "BIN2PRG"
    assert cp["op:op1"]["noTimestamps"] == "1"


def test_direction_from_ext() -> None:
    from fb2p_studio.core.extensions import direction_from_ext

    assert direction_from_ext(r"C:\a\form.scx") == "BIN2PRG"
    assert direction_from_ext(r"C:\a\form.sc2") == "PRG2BIN"
    assert direction_from_ext(r"C:\a\pj.PJX") == "BIN2PRG"
    assert direction_from_ext(r"C:\a\other.xyz") == ""
