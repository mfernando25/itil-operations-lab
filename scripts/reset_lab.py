"""Reset locally generated ITIL Operations Lab data.

Stop the lab server with Ctrl+C before running this script.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab.filesystem import remove_tree  # noqa: E402

DB = ROOT / "data" / "lab.db"
SCENARIOS = ROOT / "lab_data" / "scenarios"
STORAGE = ROOT / "lab_data" / "storage_test"


def _remove_database_files() -> None:
    for path in (DB, Path(f"{DB}-wal"), Path(f"{DB}-shm")):
        if not path.exists():
            continue
        try:
            path.unlink()
        except PermissionError:
            # A read-only attribute can survive from copied/archived lab data.
            try:
                os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
                path.unlink()
            except OSError as exc:
                raise PermissionError(
                    f"No se pudo eliminar '{path}'. Comprueba que el laboratorio "
                    "esté detenido (Ctrl+C) y vuelve a ejecutar el reinicio."
                ) from exc


def main() -> None:
    # Clean generated repositories first. If this fails, leave the database
    # untouched so the lab does not end up in a partially reset state.
    remove_tree(SCENARIOS)
    remove_tree(STORAGE)
    STORAGE.mkdir(parents=True, exist_ok=True)
    _remove_database_files()

    print("Laboratorio reiniciado correctamente.")
    print("Se eliminaron la base local y los escenarios/datasets generados.")
    print("La próxima activación generará nuevamente las evidencias e historiales.")


if __name__ == "__main__":
    main()
