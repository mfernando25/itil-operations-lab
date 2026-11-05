from __future__ import annotations

from datetime import datetime
from typing import Any

from . import database

GROUP_TITLES = {
    1: "Fallo en pruebas automatizadas",
    2: "Fallo durante la ejecución del workflow",
    3: "Problema al sincronizar cambios con Git",
    4: "Consumo anormal de CPU",
    5: "Crecimiento anormal del almacenamiento",
    6: "Incompatibilidad entre microservicios",
    7: "Información desactualizada después de la integración",
}

INITIAL = {
    1: "GitHub Actions completó una ejecución de integración continua con resultado fallido. El equipo necesita determinar si el cambio reciente puede afectar una funcionalidad del portal.",
    2: "Una ejecución de integración continua se interrumpió antes de completar el flujo previsto. El equipo debe identificar en qué etapa ocurrió y cómo recuperar la ejecución.",
    3: "Un usuario no consigue sincronizar sus cambios con el repositorio remoto. Tiene un commit local ya confirmado que debe preservarse antes de recuperar la sincronización.",
    4: "Se observa un incremento sostenido del uso de CPU en el portal de matrícula, acompañado por un aumento en los tiempos de respuesta.",
    5: "El espacio utilizado por los registros y respaldos del portal está creciendo y se aproxima al umbral operativo. El servicio continúa disponible.",
    6: "Después de integrar una actualización, la consulta del perfil de estudiante no devuelve toda la información esperada.",
    7: "Una operación de matrícula aparece registrada, pero una consulta posterior sigue mostrando un estado anterior.",
}


def _fmt_rows(rows: list[dict[str, Any]], keys: list[str]) -> str:
    if not rows:
        return "Sin registros disponibles."
    head = "| " + " | ".join(keys) + " |\n|" + "|".join(["---"] * len(keys)) + "|\n"
    body = "".join("| " + " | ".join(str(row.get(k, "—")) for k in keys) + " |\n" for row in rows)
    return head + body


def _g3_pack(pack: int) -> str:
    from .scenarios import G3_DIR
    files = {
        1: G3_DIR / "student-workspace" / "evidence" / "initial-rejection.txt",
        2: G3_DIR / "student-workspace" / "evidence" / "local-state.txt",
        3: G3_DIR / "student-workspace" / "evidence" / "remote-state.txt",
    }
    path = files.get(pack)
    if path and path.exists():
        text = path.read_text(encoding="utf-8", errors="replace")
        if pack == 3:
            diff_path = G3_DIR / "student-workspace" / "evidence" / "working-diff.txt"
            if diff_path.exists():
                text += "\n\n" + diff_path.read_text(encoding="utf-8", errors="replace")
        return text
    return "Activa el escenario G3 desde el panel del docente para generar el repositorio de práctica y las evidencias."


def build_bundle(group: int, pack: int) -> dict[str, str]:
    if group not in GROUP_TITLES or pack not in range(0, 4):
        raise ValueError("Grupo o paquete de evidencia inválido.")
    label = "Notificación inicial" if pack == 0 else f"Evidencia adicional {pack}"
    title = f"G{group} · {GROUP_TITLES[group]} · {label}"
    if pack == 0:
        content = f"# {title}\n\n{INITIAL[group]}\n\n**Solicitud al equipo:** indiquen qué información adicional necesitan y por qué."
    elif group == 3:
        content = f"# {title}\n\n{_g3_pack(pack)}"
    elif group == 1:
        texts = {
            1: "## Resumen de la ejecución\n\n- Workflow: G1 - Fallo de pruebas\n- Job: regression\n- Checkout: completado\n- Instalación de dependencias: completada\n- Resultado de la suite de regresión: failure\n- Una prueba terminó con resultado fallido.\n\nLa salida detallada de la prueba y su relación con el cambio reciente se entregan en la siguiente evidencia.",
            2: "## Log de prueba y comparación de ejecuciones\n\n- Prueba fallida: `test_enrollment_fee_after_scholarship_update`\n- Resultado esperado: `800.00`\n- Resultado obtenido: `980.00`\n- Commit reciente: `a41d9e2` — Refactor de cálculo de matrícula\n- Archivo modificado: `services/enrollment/fees.py`\n- Última ejecución exitosa: commit `91b7c40`, 09:12\n- Ejecución fallida: commit `a41d9e2`, 09:26",
            3: "## Impacto funcional observado\n\n- Funcionalidad: cálculo del importe pendiente al aplicar una beca.\n- Caso de referencia: matrícula de S/ 1,000 con beca de 20 %.\n- Resultado esperado: S/ 800.\n- Resultado observado: S/ 980.\n- No hay evidencia de afectación en consulta de cursos ni autenticación.",
        }
        content = f"# {title}\n\n{texts[pack]}"
    elif group == 2:
        texts = {
            1: "## Etapa donde se interrumpió el flujo\n\n- Workflow iniciado correctamente.\n- Checkout del repositorio: completado.\n- Etapa: Validate configuration.\n- Resultado de la etapa: failure.\n\n```text\nERROR: Required configuration variable was not available.\nProcess completed with exit code 1.\n```",
            2: "## Configuración y cambio reciente\n\n- Archivo: `.github/workflows/g2-fallo-prevalidacion.yml`\n- Commit reciente: `b73ac11` — Ajuste de variables de entorno\n- Nombre disponible en el entorno del paso: `SERVICE_ENDPOINT`.\n- Nombre requerido por la validación: `SERVICE_BASE_URL`.\n- La última ejecución exitosa ocurrió antes del cambio de configuración.",
            3: "## Alcance de la interrupción\n\n- Checkout del repositorio: completado.\n- Validación de configuración: fallida.\n- Instalación de dependencias: no iniciada.\n- Pruebas: no ejecutadas.\n- Artefactos de compilación: no generados.\n\nEl equipo debe determinar si corresponde corregir configuración, reintentar o escalar.",
        }
        content = f"# {title}\n\n{texts[pack]}"
    elif group == 4:
        rows = database.list_metrics(1000, group_number=4)
        if pack == 1:
            content = f"# {title}\n\n## Historial de cinco días\n\n{_fmt_rows(rows, ['captured_at','cpu_percent','requests_per_minute','avg_response_ms','component'])}"
        elif pack == 2:
            content = "# " + title + "\n\n## Distribución de carga observada\n\n| Componente | CPU máxima observada | Solicitudes/min | Tiempo medio |\n|---|---:|---:|---:|\n| API Matrículas | 94 % | 1,480 | 2,450 ms |\n| API Estudiantes | 68 % | 620 | 780 ms |\n| API Cursos | 43 % | 310 | 410 ms |\n\nLa muestra de mayor carga de API Matrículas coincide con el máximo de la serie histórica: 94 % de CPU, 1,480 solicitudes/min y 2,450 ms de respuesta. La degradación se concentra en el flujo de matrícula."
        else:
            content = "# " + title + "\n\n## Extracto de registros operativos\n\n```text\n10:14:02 enrollment-api WARN request_duration_ms=1980 route=/enrollments\n10:16:41 enrollment-api WARN request_duration_ms=2240 route=/enrollments\n10:19:08 enrollment-api ERROR worker queue delay=4.8s\n10:21:35 enrollment-api WARN cpu_utilization=94%\n10:22:11 gateway WARN upstream_latency_ms=2510\n```\n\nEl servicio responde, pero aumenta el tiempo de atención y la cola de solicitudes."
    elif group == 5:
        rows = database.list_metrics(1000, group_number=5)
        if pack == 1:
            converted = [{**row, "storage_used_gb": round(float(row.get("storage_used_mb") or 0) / 1024, 2)} for row in rows]
            content = f"# {title}\n\n## Evolución de almacenamiento de cinco días\n\n{_fmt_rows(converted, ['captured_at','storage_capacity_gb','storage_available_gb','storage_used_gb','component'])}"
        elif pack == 2:
            content = "# " + title + "\n\n## Distribución estimada del consumo\n\n| Ubicación | Día 1 | Día 5 | Tipo |\n|---|---:|---:|---|\n| `/var/log/enrollment` | 0.8 GB | 3.9 GB | Logs de aplicación |\n| `/srv/backups/daily` | 1.2 GB | 3.6 GB | Respaldos diarios |\n| `/var/log/gateway` | 0.4 GB | 1.2 GB | Logs de acceso |\n\nCapacidad de volumen: 10 GB. Umbral preventivo: 80 %. No se autoriza borrar respaldos sin verificar retención."
        else:
            content = "# " + title + "\n\n## Extracto de registros de crecimiento\n\n```text\n00:05 backup-job INFO backup completed size=0.82GB\n00:06 backup-job WARN previous archive retained: rotation policy=disabled\n09:00 log-manager INFO enrollment-api log size=3.9GB\n09:02 storage-monitor WARN volume usage=87% threshold=80%\n09:03 storage-monitor INFO available=1.3GB capacity=10GB\n```\n\nEl servicio continúa disponible; la alerta corresponde al riesgo de alcanzar la capacidad."
    elif group == 6:
        texts = {
            1: "## Trazas de comunicación\n\n```text\nportal-api -> students-service GET /students/STU-1042\nstudents-service -> portal-api HTTP 200\nportal-api WARN profile mapping incomplete\nportal-api -> browser HTTP 502\n```\n\nLa consulta al servicio de estudiantes responde, pero el portal no completa la composición del perfil.",
            2: "## Solicitud y respuesta observadas\n\nSolicitud: `GET /students/STU-1042`\n\nRespuesta recibida:\n```json\n{\"studentId\":\"STU-1042\",\"name\":\"Estudiante de prueba\",\"courseId\":\"CS-204\"}\n```\n\nEl consumidor no logra mapear uno de los atributos recibidos.",
            3: "## Historial de integración\n\n- Servicio consumidor: `enrollment-service` v2.3.0.\n- Servicio proveedor: `students-service` v2.4.0.\n- Commit de integración: `c82f190`.\n- La suite unitaria del proveedor terminó correctamente.\n- No existe una prueba de contrato entre ambos componentes en el pipeline actual.",
        }
        content = f"# {title}\n\n{texts[pack]}"
    else:
        texts = {
            1: "## Identificación de la operación\n\n- Operación: `ENR-78421`.\n- Identificador académico: `STU-1042`.\n- Hora de registro: 10:32:14.\n- Resultado de escritura: HTTP 200; estado `Confirmada`.\n- Hora de consulta posterior: 10:32:19.\n- Resultado de consulta: `Pendiente`.",
            2: "## Trazas de escritura y lectura\n\n```text\n10:32:14 enrollment-service INFO update ENR-78421 status=Confirmada\n10:32:14 enrollment-service INFO transaction committed\n10:32:15 cache-service INFO key enrollment:STU-1042 retained\n10:32:19 portal-api INFO cache hit key=enrollment:STU-1042 status=Pendiente\n```",
            3: "## Historial de integración\n\n- Commit: `d91b0a7` — Separación de lectura y escritura de matrícula.\n- Servicio de escritura: `enrollment-service` v2.5.0.\n- Servicio de consulta: `portal-query` v1.8.2.\n- La actualización de datos se confirmó; no se observa una operación de invalidación en el registro de caché.\n- No se detectan fallos de persistencia en la operación indicada.",
        }
        content = f"# {title}\n\n{texts[pack]}"
    return {"title": title, "filename": f"G{group}_evidencia_{pack}.md", "markdown": content}


def instructor_diagnostics() -> dict[int, str]:
    return {
        1: "La implementación de cálculo utiliza el porcentaje como importe fijo en lugar de multiplicarlo por la base. La prueba de regresión detecta la diferencia.",
        2: "El workflow solicita SERVICE_BASE_URL, pero la configuración existente usa SERVICE_ENDPOINT. La validación detiene la pipeline antes de tests.",
        3: "La rama local contiene un commit ya confirmado que modificó el archivo de configuración; main avanzó con otro commit sobre la misma línea. El pull produce un conflicto de merge. Preservar y reconciliar ambos commits antes de completar.",
        4: "El escenario genera diez puntos distribuidos en cinco fechas de CPU, solicitudes y latencia. La muestra máxima de enrollment-api es 94 % de CPU, 1,480 solicitudes/min y 2,450 ms. Datos del caso, no telemetría histórica de la laptop.",
        5: "El escenario genera diez puntos distribuidos en cinco fechas para un volumen lógico de 10 GB. El uso sube de 2.4 GB a 8.7 GB (87 %); el crecimiento se concentra en logs y respaldos sin rotación. No borrar sin validar retención.",
        6: "El proveedor responde studentId/courseId en camelCase, mientras el consumidor espera student_id/course_id en snake_case. Es una incompatibilidad de contrato entre servicios.",
        7: "La escritura se confirma en la base principal, pero la caché conserva Pendiente. La solución de demostración es invalidar/actualizar la caché, no alterar el registro principal.",
    }
