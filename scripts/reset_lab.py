from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "lab.db"
STORAGE = ROOT / "lab_data" / "storage_test"
if DB.exists():
    DB.unlink()
if STORAGE.exists():
    shutil.rmtree(STORAGE)
STORAGE.mkdir(parents=True, exist_ok=True)
print("Laboratorio reiniciado. Se eliminaron la base local y los archivos temporales de prueba.")
