"""Lanza el driver VFP como QProcess.

- Genera un tempdir por job con `job.ini` y `events.jsonl`.
- Configura `FB2P_JOB` en el entorno del hijo.
- Corre `vfp9.exe -T -C <bridge.fpw>` con cwd = vfp_bridge/.
- Expone senales de EventStream y de terminacion del proceso.
"""

from __future__ import annotations

import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from fb2p_studio.core.discovery import Paths
from fb2p_studio.core.ipc import EventStream
from fb2p_studio.core.job import Job


@dataclass(slots=True, frozen=True)
class BridgeLaunchError(Exception):
    """Fallo antes de arrancar el driver — vfp9.exe / FoxBin2Prg / bridge no encontrados."""

    reason: str

    def __str__(self) -> str:
        return self.reason


class Bridge(QObject):
    """Runner de una unica job.

    Uso:
        bridge = Bridge(paths)
        bridge.events.job_done.connect(...)
        bridge.finished.connect(...)
        bridge.start(job)
    """

    finished = Signal(int)             # exit code del vfp9.exe
    stdout_line = Signal(str)          # linea de stdout del proceso (raro, pero por si acaso)
    stderr_line = Signal(str)

    def __init__(self, paths: Paths, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._paths = paths
        self._workdir: Path | None = None
        self._proc: QProcess | None = None
        self.events: EventStream | None = None

    # ------------------------------------------------------------------
    def start(self, job: Job) -> None:
        if self._paths.vfp_exe is None:
            raise BridgeLaunchError("No se encontro vfp9.exe. Configura la ruta en Preferencias.")
        if self._paths.fb2p_home is None:
            raise BridgeLaunchError("No se encontro FoxBin2Prg (EXE/FXP). Configura FB2P_HOME en Preferencias.")
        if not (self._paths.bridge_dir / "fb2p_bridge.prg").exists():
            raise BridgeLaunchError(f"No se encontro el driver: {self._paths.bridge_dir}\\fb2p_bridge.prg")

        self._workdir = Path(tempfile.mkdtemp(prefix=f"fb2p_studio_{uuid.uuid4().hex[:8]}_"))
        job_ini = self._workdir / "job.ini"
        events_path = self._workdir / "events.jsonl"

        # Job efectivo: home y event_stream los fija la GUI (no lo que trajo el llamador).
        effective_job = Job(
            foxbin2prg_home=str(self._paths.fb2p_home),
            event_stream=events_path,
            operations=job.operations,
            dry_run=job.dry_run,
        )
        job_ini.write_text(effective_job.to_ini(), encoding="utf-8")
        events_path.touch()

        self.events = EventStream(events_path, self)
        self.events.start()

        env = QProcessEnvironment.systemEnvironment()
        env.insert("FB2P_JOB", str(job_ini))

        self._proc = QProcess(self)
        self._proc.setProgram(str(self._paths.vfp_exe))
        self._proc.setArguments(["-T", "-C", str(self._paths.bridge_dir / "fb2p_bridge.fpw")])
        self._proc.setWorkingDirectory(str(self._paths.bridge_dir))
        self._proc.setProcessEnvironment(env)
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.finished.connect(self._on_finished)
        self._proc.start()

    # ------------------------------------------------------------------
    def cancel(self) -> None:
        """Solicita cancelacion cooperativa: sentinela .cancel en el workdir."""
        if self._workdir is not None:
            (self._workdir / ".cancel").touch()

    # ------------------------------------------------------------------
    def _on_stdout(self) -> None:
        assert self._proc is not None
        data = bytes(self._proc.readAllStandardOutput()).decode("cp1252", errors="replace")
        for line in data.splitlines():
            if line.strip():
                self.stdout_line.emit(line)

    def _on_stderr(self) -> None:
        assert self._proc is not None
        data = bytes(self._proc.readAllStandardError()).decode("cp1252", errors="replace")
        for line in data.splitlines():
            if line.strip():
                self.stderr_line.emit(line)

    def _on_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        if self.events is not None:
            self.events.stop()
        self.finished.emit(exit_code)

    # ------------------------------------------------------------------
    @property
    def workdir(self) -> Path | None:
        return self._workdir
