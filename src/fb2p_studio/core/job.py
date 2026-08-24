"""Modelo tipado del job y sus eventos.

Un `Job` es la unidad de trabajo que se envia al bridge VFP. Se serializa como
un archivo INI (formato que VFP procesa trivialmente). El bridge devuelve
eventos JSONL que se deserializan aqui a los dataclasses `*Event`.
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Input: Job / Operation
# ---------------------------------------------------------------------------

Direction = Literal["", "BIN2PRG", "PRG2BIN"]


@dataclass(slots=True)
class OperationOptions:
    """Opciones pasadas a c_foxbin2prg.execute() por operacion."""

    no_timestamps: int = 1
    debug: int = 0
    recompile: int = 1
    backup_levels: int = 1
    clear_unique_id: int = 1
    cfg_file: str = ""
    output_folder: str = ""


@dataclass(slots=True)
class Operation:
    """Una unica invocacion de FoxBin2Prg sobre un archivo o carpeta."""

    id: str
    file: str
    type: Direction = ""
    options: OperationOptions = field(default_factory=OperationOptions)


@dataclass(slots=True)
class Job:
    """Conjunto de operaciones + configuracion comun."""

    foxbin2prg_home: str
    event_stream: Path
    operations: list[Operation]
    dry_run: bool = False

    def to_ini(self) -> str:
        """Serializa el job a INI en el formato que consume el bridge VFP."""
        cp = configparser.ConfigParser(interpolation=None)
        cp["job"] = {
            "foxbin2prgHome": self.foxbin2prg_home,
            "eventStream": str(self.event_stream),
            "dryRun": "1" if self.dry_run else "0",
        }
        for op in self.operations:
            section = f"op:{op.id}"
            cp[section] = {
                "file": op.file,
                "type": op.type,
                "noTimestamps": str(op.options.no_timestamps),
                "debug": str(op.options.debug),
                "recompile": str(op.options.recompile),
                "backupLevels": str(op.options.backup_levels),
                "clearUniqueID": str(op.options.clear_unique_id),
                "cfgFile": op.options.cfg_file,
                "outputFolder": op.options.output_folder,
            }
        from io import StringIO

        buf = StringIO()
        cp.write(buf)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Output: eventos JSONL emitidos por el driver
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class JobStartEvent:
    total: int
    timestamp: str
    vfp_version: str
    fb2p_version: str
    dry_run: bool


@dataclass(slots=True)
class OpStartEvent:
    op_id: str
    file: str
    direction: str


@dataclass(slots=True)
class FileProcessedEvent:
    op_id: str
    file: str
    in_out: str  # "I" input | "O" output
    processed: bool
    has_errors: bool
    supported: bool
    expanded: bool


@dataclass(slots=True)
class OpDoneEvent:
    op_id: str
    return_code: int
    elapsed_ms: int


@dataclass(slots=True)
class OpErrorEvent:
    op_id: str
    error_no: int
    message: str
    line_no: int
    line_contents: str
    details: str
    elapsed_ms: int


@dataclass(slots=True)
class JobDoneEvent:
    ok_count: int
    err_count: int
    elapsed_ms: int


@dataclass(slots=True)
class DriverErrorEvent:
    message: str
    stage: str


@dataclass(slots=True)
class CancelledEvent:
    ops_processed: int


Event = (
    JobStartEvent
    | OpStartEvent
    | FileProcessedEvent
    | OpDoneEvent
    | OpErrorEvent
    | JobDoneEvent
    | DriverErrorEvent
    | CancelledEvent
)


def parse_event(payload: dict) -> Event | None:
    """Convierte un dict JSON del bridge en el dataclass correspondiente."""
    kind = payload.get("event")
    if kind == "job_start":
        return JobStartEvent(
            total=int(payload["total"]),
            timestamp=payload.get("timestamp", ""),
            vfp_version=payload.get("vfpVersion", ""),
            fb2p_version=payload.get("fb2pVersion", ""),
            dry_run=bool(payload.get("dryRun", 0)),
        )
    if kind == "op_start":
        return OpStartEvent(
            op_id=payload["opId"],
            file=payload["file"],
            direction=payload.get("direction", ""),
        )
    if kind == "file_processed":
        return FileProcessedEvent(
            op_id=payload["opId"],
            file=payload["file"],
            in_out=payload.get("inOut", ""),
            processed=bool(payload.get("processed", 0)),
            has_errors=bool(payload.get("hasErrors", 0)),
            supported=bool(payload.get("supported", 0)),
            expanded=bool(payload.get("expanded", 0)),
        )
    if kind == "op_done":
        return OpDoneEvent(
            op_id=payload["opId"],
            return_code=int(payload.get("returnCode", 0)),
            elapsed_ms=int(payload.get("elapsedMs", 0)),
        )
    if kind == "op_error":
        return OpErrorEvent(
            op_id=payload["opId"],
            error_no=int(payload.get("errorNo", 0)),
            message=payload.get("message", ""),
            line_no=int(payload.get("lineNo", 0)),
            line_contents=payload.get("lineContents", ""),
            details=payload.get("details", ""),
            elapsed_ms=int(payload.get("elapsedMs", 0)),
        )
    if kind == "job_done":
        return JobDoneEvent(
            ok_count=int(payload.get("okCount", 0)),
            err_count=int(payload.get("errCount", 0)),
            elapsed_ms=int(payload.get("elapsedMs", 0)),
        )
    if kind == "driver_error":
        return DriverErrorEvent(
            message=payload.get("message", ""),
            stage=payload.get("stage", ""),
        )
    if kind == "cancelled":
        return CancelledEvent(ops_processed=int(payload.get("opsProcessed", 0)))
    return None
