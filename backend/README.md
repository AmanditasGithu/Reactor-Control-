# Backend – Control del Reactor

API en Python con **FastAPI**, base de datos **PostgreSQL** (vía SQLAlchemy).

## Estructura

```
backend/
├── app/
│   ├── main.py        ← arranca la API
│   ├── config.py      ← configuración (dirección de la base de datos)
│   ├── database.py    ← conexión con PostgreSQL
│   └── models.py      ← tablas de la base de datos
├── tests/             ← pruebas automáticas (pytest)
├── requirements.txt   ← librerías de Python
└── Dockerfile
```

## Correr con Docker (recomendado)

Desde la carpeta raíz del repo:

```
docker compose up --build
```

- API: http://localhost:8000
- Documentación interactiva (para probar los endpoints): http://localhost:8000/docs

Para apagarlo: `Ctrl + C`, y luego `docker compose down`.

## Correr sin Docker (Windows, PowerShell)

Desde la carpeta `backend`:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:DATABASE_URL="sqlite:///./local.db"
uvicorn app.main:app --reload
```

Si `activate` da error de "ejecución de scripts deshabilitada", correr una vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Correr las pruebas

Con el entorno virtual activo, desde la carpeta `backend`:

```
pytest
```

Las pruebas usan SQLite en memoria, así que no necesitan PostgreSQL ni Docker.