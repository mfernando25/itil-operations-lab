# ITIL Operations Lab · v0.2.3

Laboratorio académico de operaciones TI e ITIL 4 para investigar siete eventos de un portal universitario. La solución genera datos, historiales y evidencias de escenario al momento de activarlos; no necesita esperar cinco días de recolección.

## Inicio rápido en Windows

```powershell
git clone https://github.com/mfernando25/itil-operations-lab.git
cd itil-operations-lab
.\scripts\setup_windows.ps1
.\scripts\start_lab.ps1
```

- **Vista de estudiantes:** http://127.0.0.1:8000
- **Panel privado del docente:** http://127.0.0.1:8000/instructor

El repositorio es público. Los estudiantes pueden inspeccionar código fuente, commits, workflows y ejecuciones como parte de su investigación. Se espera que delimiten su búsqueda al grupo asignado y fundamenten sus decisiones; la evaluación se centra en el razonamiento y la atención propuesta, no en adivinar una causa oculta.

Mantén abierta la ventana de PowerShell durante la sesión. Detén el servidor con `Ctrl+C`.

## Requisitos

- Windows 10/11 (probado como entorno principal), Python 3.10 o superior y Git en PATH.
- La versión local no requiere Docker ni cuentas personales de estudiantes.
- Para los grupos 1 y 2 se necesita acceso al repositorio GitHub y a su pestaña Actions.

## Los siete grupos

| Grupo | Evento | Mecanismo de demostración |
|---|---|---|
| 1 | Fallo en pruebas automatizadas | GitHub Actions ejecuta una prueba de regresión deliberadamente fallida y publica logs como artefacto. |
| 2 | Fallo durante el workflow | GitHub Actions detiene la ejecución durante una validación de configuración, antes de iniciar tests. |
| 3 | Sincronización Git | Se construye un repositorio local aislado con rama remota y local divergentes; el pull produce un conflicto reproducible. |
| 4 | CPU anormal | Se generan diez muestras distribuidas en cinco días con CPU, solicitudes/minuto y latencia correlacionadas. |
| 5 | Crecimiento de almacenamiento | Se generan diez puntos de capacidad/espacio disponible y desglose de logs y respaldos en un volumen lógico de 10 GB. |
| 6 | Incompatibilidad entre servicios | El proveedor cambia campos del contrato y el consumidor no puede completar el perfil. |
| 7 | Información desactualizada | La escritura se confirma en el registro principal, mientras la caché conserva el estado anterior. |

## Historiales de cinco días: cómo funcionan

G4 y G5 crean sus series históricas al pulsar **Preparar / activar** en el panel docente. Cada grupo genera exactamente diez puntos, dos por fecha, distribuidos en cinco fechas consecutivas; la evidencia queda disponible inmediatamente.

Esos datos son **historial del caso generado para la actividad**, no registros históricos reales de la laptop. La separación de fuentes es intencional:

- **G4:** CPU, solicitudes por minuto y latencia utilizan el historial sintético de cinco días. Memoria y disco continúan mostrando las mediciones reales del equipo.
- **G5:** el almacenamiento del servicio utiliza el historial sintético de cinco días. CPU, memoria y disco continúan mostrando las mediciones reales del equipo.
- Fuera de G4/G5, los gráficos muestran las mediciones reales disponibles durante la sesión. Los títulos y rótulos identifican la procedencia y la ventana temporal de cada serie.

Al reiniciar G4 o G5 se eliminan las muestras sintéticas de esa ejecución. Una nueva activación también reemplaza cualquier serie previa del mismo grupo, por lo que el dashboard y los paquetes de evidencia contienen exactamente diez muestras y no acumulan duplicados. Las métricas reales del equipo se siguen registrando aparte, cada 60 segundos por defecto.

G5 modela un volumen lógico de 10 GB. Solo se escribe un pequeño archivo descriptivo; no se crean archivos de varios gigabytes ni se llena el disco real.

## Flujo del docente

1. Abre `/instructor` en tu laptop.
2. Pulsa **Preparar / activar** para el grupo asignado. La activación genera el evento y, cuando corresponde, el dataset o repositorio de práctica.
3. Abre **Preparar evidencia para correo**, selecciona grupo y paquete y descarga el Markdown.
4. Envía primero la notificación inicial (paquete 0). Entrega los paquetes 1, 2 y 3 según las solicitudes justificadas de los equipos.
5. Consulta **Notas internas** solo desde el panel docente. No compartas esa consola.

Cada grupo dispone de una notificación inicial y tres paquetes adicionales. Los paquetes son materiales de apoyo para la investigación; el estudiante debe explicar qué información necesita y por qué.

## GitHub Actions: grupos 1 y 2

En el panel docente usa el enlace a Actions:

- `G1 - Fallo de pruebas`: ejecuta una prueba de regresión que falla. El workflow guarda logs, resultado JUnit, revisión ejecutada, historial de commits de los archivos de la prueba y archivos modificados en el artefacto `G1-evidencia-ejecucion`.
- `G2 - Fallo de prevalidación`: detiene el flujo antes de instalar dependencias y ejecutar pruebas. Guarda la salida, configuración, revisión ejecutada e historial real de cambios del workflow en `G2-evidencia-prevalidacion`.

Las referencias `c82f190` (G6) y `d91b0a7` (G7) son identificadores del sistema académico ficticio, no commits del repositorio GitHub.

Descarga cada artefacto desde la ejecución correspondiente en GitHub Actions. La CI normal de `main` ejecuta la suite del proyecto y debe permanecer aprobada.

## Grupo 3: repositorio de práctica aislado

Al activar G3 se crea `lab_data/scenarios/g3/student-workspace`, un repositorio local de práctica. No modifica el repositorio Git de este proyecto. Los archivos `evidence/` que contiene documentan el rechazo, el estado local y el estado remoto. Git debe estar instalado y disponible en PATH.

## Grupos 6 y 7: comprobación funcional

En la vista de estudiantes:

- La consulta de perfil permite observar la degradación después de activar G6.
- La consulta de matrícula permite comparar el estado disponible antes y después de activar G7.

En el panel docente se puede reiniciar cada escenario. En G7, el docente utiliza **Reconciliar caché G7** desde la sección de recuperación supervisada, después de que el equipo haya presentado y justificado su propuesta. La vista de estudiantes no dispone de ese control.

## Arquitectura y alcance

La versión local es una aplicación ligera Python con límites lógicos separados para estudiantes, cursos y matrículas, un servidor HTTP local y SQLite. Esta versión prioriza instalación simple y reproducibilidad para la sesión en aula; los límites de servicio se simulan dentro de un mismo proceso y **todavía no son tres contenedores FastAPI independientes**. No se debe presentar como una arquitectura de microservicios desplegada en Docker.

## Pruebas y reinicio

Detén primero el servidor con `Ctrl+C`. Después ejecuta:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\reset_lab.py
```

El reinicio elimina la base local y los repositorios/datasets generados. La limpieza de carpetas incluye un reintento compatible con Windows para archivos con atributo de solo lectura, incluidos los hooks de los repositorios Git de práctica. Si Windows mantiene un bloqueo por una terminal, editor o Explorador abierto, el script informa la ruta y conserva la base de datos hasta completar la limpieza. No modifica commits del repositorio GitHub. Después de reiniciar, activa nuevamente los grupos para regenerar sus evidencias.

## Vista compartida por grupo

En el panel docente selecciona el grupo que se está atendiendo y pulsa **Aplicar vista**. La vista estudiantil muestra únicamente los eventos y las series históricas del grupo asignado. Al activar un escenario, se asigna automáticamente ese grupo; al reiniciarlo, se limpia la asignación si corresponde. Esta separación evita revelar accidentalmente eventos de otros equipos, pero no oculta el código público ni sustituye la responsabilidad de investigar el caso asignado.

## Seguridad

- El servidor se enlaza a `127.0.0.1`; no lo expongas a la red local.
- No uses datos reales de estudiantes ni secretos en el repositorio.
- La ruta `/instructor` y sus endpoints son una consola local sin autenticación: no compartas esa URL ni ejecutes el servidor en una interfaz de red pública.
- El archivo `INSTRUCTOR_RUNBOOK_PRIVATE.md` es para el docente y no debe subirse al repositorio público.
