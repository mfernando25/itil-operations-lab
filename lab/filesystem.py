"""Windows-friendly cleanup helpers for generated lab data."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import time
from pathlib import Path
from typing import Union

PathLike = Union[str, os.PathLike[str]]


def _retry_remove_error(function, path: str, exc_info) -> None:
    """Make a failed path writable and retry the failed removal operation."""
    original_error = exc_info[1]

    try:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    except OSError:
        pass

    if os.name == "nt":
        # Git's sample hooks or copied files can carry the Windows read-only
        # attribute, which is not always cleared by chmod alone.
        try:
            subprocess.run(
                ["attrib", "-R", "/S", "/D", path],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            pass

    try:
        function(path)
    except OSError as retry_error:
        raise retry_error from original_error


def remove_tree(path: PathLike, attempts: int = 3) -> None:
    """Remove a generated directory, tolerating transient Windows permissions.

    The function is intentionally limited to paths supplied by the lab's
    cleanup routines. It does not alter ACLs or take ownership of files.
    """
    target = Path(path)
    if not target.exists():
        return
    if target.is_symlink() or not target.is_dir():
        raise NotADirectoryError(f"Se esperaba una carpeta para limpiar: {target}")

    for attempt in range(max(1, attempts)):
        try:
            shutil.rmtree(target, onerror=_retry_remove_error)
            return
        except FileNotFoundError:
            return
        except PermissionError as exc:
            if os.name == "nt" and attempt < attempts - 1:
                try:
                    subprocess.run(
                        ["attrib", "-R", "/S", "/D", str(target)],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                except OSError:
                    pass
                time.sleep(0.25 * (attempt + 1))
                continue
            raise PermissionError(
                f"No se pudo eliminar '{target}'. Detén el laboratorio y cierra "
                "cualquier terminal, editor o ventana del Explorador que esté "
                "usando esa carpeta; después vuelve a ejecutar el reinicio."
            ) from exc
