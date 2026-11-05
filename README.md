# ITIL Operations Lab

Laboratorio local para una simulación académica de operaciones TI e ITIL 4.

## Componentes

- Portal universitario de demostración.
- Dashboard local de CPU, memoria, disco e histórico de métricas.
- Registro de eventos en SQLite.
- Controles locales para activar escenarios de laboratorio.
- Script PowerShell para capturar un error local de Git.
- GitHub Actions: CI normal y workflows de demostración.
- Pruebas automatizadas de la funcionalidad base.

> Entorno educativo. No contiene servicios universitarios reales ni debe conectarse a datos reales.

## Requisitos

- Python 3.10 o superior (recomendado 3.11+).
- Git.
- Windows 10/11, macOS o Linux.

## Instalación en Windows PowerShell

```powershell
git clone https://github.com/mfernando25/itil-operations-lab.git
cd itil-operations-lab
.\scripts\setup_windows.ps1
.\scripts\start_lab.ps1
```

Abre `http://127.0.0.1:8000`. Si PowerShell bloquea los scripts en esa sesión, ejecuta:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

También puedes crear un entorno virtual manualmente con `py -m venv .venv`, activarlo e instalar `requirements.txt`.

## Ejecutar en otra computadora

Clona el mismo repositorio e instala las dependencias en esa PC. No copies la carpeta `.venv`: cada computadora debe crear su propio entorno virtual.

## Monitoreo

- Las métricas reales corresponden al equipo donde se ejecuta el laboratorio.
- El servidor registra CPU, memoria, disco y uso de la carpeta de prueba en SQLite cada 60 segundos por defecto.
- Mantén el servidor activo para recopilar histórico real.
- Los datos agregados por los escenarios se identifican como `simulated`.
- Exporta las últimas 120 horas a CSV con `python scripts/export_metrics.py --hours 120`.

El intervalo se puede cambiar con `MONITOR_INTERVAL_SECONDS` (mínimo 5 segundos).

## Pruebas

```powershell
python -m pytest -q
```

La suite normal usa `tests/`. Los workflows de escenario se lanzan manualmente desde **Actions** o mediante push a sus ramas dedicadas (`scenario/group1` y `scenario/group2`). El fallo deliberado de G1 está aislado para no romper la CI normal de `main`.

## Reiniciar

```powershell
python scripts/reset_lab.py
```

Esto reinicia la base de datos local y archivos temporales de prueba; no cambia código ni commits.

## Estructura

```text
app.py
lab/                  lógica, servidor, métricas y escenarios
web/                  interfaz del dashboard
tests/                pruebas normales
scenario_tests/       pruebas aisladas de demostración
scripts/              instalación, ejecución, reset y exportación
.github/workflows/    CI y workflows de escenarios
data/                 base de datos local (ignorada por Git)
lab_data/             datos de prueba
```

## Seguridad y operación

- No publiques tokens, contraseñas, archivos `.env` ni información personal.
- Mantén el servidor enlazado a `127.0.0.1` durante la clase.
- No uses información real de estudiantes.
- CPU y almacenamiento de los escenarios son simulaciones acotadas: no saturan el procesador ni llenan el disco.

## Workflows

- `CI - Pruebas normales`: se ejecuta en `main`.
- `G1 - Fallo de pruebas`: falla intencionalmente en la prueba de regresión cuando se lanza desde Actions o desde `scenario/group1`.
- `G2 - Fallo de prevalidación`: falla antes de las pruebas si no existe la variable de repositorio `LAB_SERVICE_ENDPOINT`; es un fallo deliberado de la demostración.

Para los workflows, consulta el historial de ejecuciones en la pestaña **Actions**.
