"""Verifica el parser de eventos JSONL."""

from __future__ import annotations

import json

from fb2p_studio.core.job import (
    DriverErrorEvent,
    FileProcessedEvent,
    JobDoneEvent,
    JobStartEvent,
    OpDoneEvent,
    OpErrorEvent,
    OpStartEvent,
    parse_event,
)


def test_parse_job_start() -> None:
    ev = parse_event(json.loads(
        '{"event":"job_start","total":3,"timestamp":"2026-08-24T10:30:00",'
        '"vfpVersion":"09.00.0000.7423","fb2pVersion":"1.21.5","dryRun":0}'
    ))
    assert isinstance(ev, JobStartEvent)
    assert ev.total == 3
    assert ev.fb2p_version == "1.21.5"
    assert ev.dry_run is False


def test_parse_op_error() -> None:
    ev = parse_event(json.loads(
        '{"event":"op_error","opId":"op2","errorNo":11,"message":"boom",'
        '"lineNo":842,"lineContents":"","details":"","elapsedMs":42}'
    ))
    assert isinstance(ev, OpErrorEvent)
    assert ev.error_no == 11
    assert ev.line_no == 842


def test_parse_all_kinds() -> None:
    kinds = [
        ('{"event":"op_start","opId":"o","file":"f","direction":"BIN2PRG"}', OpStartEvent),
        ('{"event":"file_processed","opId":"o","file":"f","inOut":"O",'
         '"processed":1,"hasErrors":0,"supported":1,"expanded":1}', FileProcessedEvent),
        ('{"event":"op_done","opId":"o","returnCode":0,"elapsedMs":10}', OpDoneEvent),
        ('{"event":"job_done","okCount":2,"errCount":0,"elapsedMs":100}', JobDoneEvent),
        ('{"event":"driver_error","message":"m","stage":"s"}', DriverErrorEvent),
    ]
    for raw, cls in kinds:
        ev = parse_event(json.loads(raw))
        assert isinstance(ev, cls), f"esperaba {cls}, obtuve {type(ev)} para {raw}"


def test_parse_unknown_returns_none() -> None:
    assert parse_event({"event": "not_a_real_event"}) is None
