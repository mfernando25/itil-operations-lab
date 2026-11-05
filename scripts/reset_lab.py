from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "lab.db"
SCENARIOS = ROOT / "lab_data" / "scenarios"
STORAGE = ROOT / "lab_data" / "storage_test"
if DB.exists():
    DB.unlink()
if SCENARIOS.exists():
    shutil.rmtree(SCENARIOS)
STORAGE.mkdir(parents=True, exist_ok=True)
for child in STORAGE.iterdir():
    if child.is_file():
        child.unlink()
print("Laboratorio reiniciado: base local, escenarios generados y archivos temporales eliminados.")
print("La próxima activación generará nuevamente evidencias e historiales.")
