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
    ProgressEvent,
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
        ('{"event":"progress","opId":"o","current":3,"total":10,"text":"x"}', ProgressEvent),
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


def test_parse_progress() -> None:
    texto = "Procesando C:/p/año.scx..."
    ev = parse_event(json.loads(json.dumps(
        {"event": "progress", "opId": "proyecto", "current": 12, "total": 1040, "text": texto}
    )))
    assert isinstance(ev, ProgressEvent)
    assert (ev.op_id, ev.current, ev.total) == ("proyecto", 12, 1040)
    assert ev.text == texto
