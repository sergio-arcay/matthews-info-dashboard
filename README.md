# Matthews Info Dashboard

Aplicación web con backend y frontend integrados. El backend define la distribución de bloques, expone el HTML de cada bloque y controla los tiempos de actualización. El frontend recibe esa configuración, renderiza los bloques y refresca cada uno de forma paralela e independiente.

## Requisitos

- Python 3.13+
- Poetry

## Instalación y ejecución

```bash
poetry install
poetry run dev
```

Luego abre `http://localhost:8000`.

## Docker

```bash
docker compose up --build
```

El servicio expone `http://localhost:8000`.

## Endpoints

- `GET /` → Frontend (dashboard).
- `GET /api/layout` → Distribución completa del dashboard (grid + bloques + tiempos).
- `GET /api/layout?panel=raspi-dashboard` → Layout personalizado (2x2 con clock).
- `GET /api/blocks/{block_id}` → HTML + tiempo de actualización para un bloque específico.
- `GET /api/health` → Health check.

### Ejemplo de `/api/layout`

```json
{
  "generated_at": "2026-03-05T10:20:30Z",
  "grid": {"columns": 12, "row_height": 120, "gap": 12, "padding": 16},
  "blocks": [
    {
      "id": "clock",
      "title": "Hora actual",
      "refresh_seconds": 5,
      "position": {"col": 1, "row": 1, "col_span": 4, "row_span": 2},
      "min_height": 252
    }
  ]
}
```

### Ejemplo de `/api/blocks/clock`

```json
{
  "id": "clock",
  "title": "Hora actual",
  "html": "<div class=\"block-header\">...",
  "scripts_before": [],
  "scripts_after": ["..."],
  "refresh_seconds": 5,
  "updated_at": "2026-03-05T10:20:31Z",
  "meta": {}
}
```

## Estructura del proyecto

- `src/mid/main.py` → FastAPI, endpoints y publicación del frontend.
- `src/mid/blocks/` → Bloques individuales (una clase por archivo).
- `src/mid/blocks/base.py` → Clases base y contratos para bloques.
- `src/mid/blocks/registry.py` → Descubrimiento automático de bloques.
- `src/mid/layout/engine.py` → Generación del layout a partir de los bloques.
- `src/mid/layout/panels.py` → Layouts personalizados por panel.
- `src/mid/layout/schemas.py` → Esquemas JSON (Pydantic).
- `src/mid/frontend/` → HTML/CSS/JS del dashboard.

## Flujo de funcionamiento

1. El frontend pide `GET /api/layout` (o `?panel=...`).
2. El backend responde con la distribución del grid y el listado de bloques.
3. El frontend crea los contenedores usando la distribución recibida.
4. En paralelo, el frontend llama a `GET /api/blocks/{id}` para cada bloque.
5. Cada bloque responde con `html` y su `refresh_seconds`.
6. El frontend programa la siguiente actualización individual de ese bloque.

## Crear nuevos bloques

Cada bloque es **una clase única en su propio archivo**, con la misma interfaz. Pasos:

1. Crear un archivo nuevo en `src/mid/blocks/`, por ejemplo `weather.py`.
2. Definir una clase que herede `BaseBlock`.
3. Implementar `render()` y devolver `BlockRender`.
4. Asignar `id`, `title`, `refresh_seconds`, `col_span`, `row_span` y opcionalmente `col`/`row`.

Ejemplo:

```python
from mid.blocks.base import BaseBlock, BlockRender

class WeatherBlock(BaseBlock):
    id = "weather"
    title = "Clima"
    refresh_seconds = 60
    col_span = 6
    row_span = 2
    col = 1
    row = 5
    order = 50

    def render(self) -> BlockRender:
        html = """
        <div class=\"block-header\">
            <h2 class=\"block-title\">Clima</h2>
            <span class=\"block-tag\">Ciudad</span>
        </div>
        <div class=\"block-body\">
            <p>22°C · Soleado</p>
        </div>
        """.strip()
        return BlockRender(html=html, refresh_seconds=self.refresh_seconds)
```

El registro es automático. No hay que tocar más archivos: el backend detecta módulos dentro de `mid.blocks`.

### Reglas para el HTML del bloque

- Solo HTML (sin `<script>`).
- Usa clases existentes (`block-header`, `block-title`, `block-body`) para estilos coherentes.
- Puedes añadir clases propias para estilos específicos en `styles.css`.

### Scripts por bloque (frontend)

Además del HTML, un bloque puede devolver uno o varios scripts JS que el frontend ejecuta:

- `scripts_before`: se ejecuta antes de reemplazar el HTML del bloque.
- `scripts_after`: se ejecuta después de reemplazar el HTML del bloque.

Cada script recibe un objeto `context` con:

- `blockId`
- `blockEl` (contenedor del bloque en el DOM)
- `data` (respuesta completa del backend)

Ejemplo mínimo:

```python
return BlockRender(
    html=html,
    refresh_seconds=self.refresh_seconds,  # None para desactivar refresco
    scripts_after=[
        "context.blockEl.querySelector('.mi-clase').textContent = 'Hola';",
    ],
)
```

## Personalizar el layout

La distribución se genera en `src/mid/layout/engine.py`:

- Si defines `col` y `row` en el bloque, se respeta esa posición.
- Si no defines posición, el motor ubica el bloque en el primer espacio disponible.
- El tamaño lo controlan `col_span` y `row_span`.

Puedes cambiar la grilla global en `default_grid()`:

```python
return GridConfig(columns=10, row_height=140, gap=16, padding=20)
```

Si `row_height` es `null` o `<= 0`, el frontend calcula automáticamente la altura
de fila para rellenar el alto disponible del dashboard según el número de filas.

## Frontend

El frontend no conoce los bloques; solo interpreta lo que envía el backend.

- `app.js` construye el grid y refresca cada bloque en paralelo.
- Si la URL incluye `?panel=...`, solicita ese panel al backend.
- Cada bloque usa el `refresh_seconds` de la última respuesta del backend.
- Si un bloque falla, se reintenta automáticamente cada 10 segundos.
- Si `refresh_seconds` es `null` o `<= 0`, no se agenda refresco automático para ese bloque.
