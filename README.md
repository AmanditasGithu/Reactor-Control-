# Control del Reactor

CE-1105 Principios de Modelado en Ingeniería · TEC · II Semestre 2026

Juego multijugador con control físico (Arduino): los jugadores recorren la arena, evitan a los
guardianes y extraen energía del reactor.

## Requisitos

- Python 3.12 o superior
- (Opcional) Arduino Mega con `Botones_Reactor_control.ino` cargado, conectado por USB

## Cómo correr el juego

### La primera vez (una sola vez por computadora)

Desde la carpeta principal del repositorio:

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r ..\frontend\requirements.txt
```

### Cada vez que se quiera jugar

**Terminal 1 – backend** (dejarla abierta):

```
cd backend
.venv\Scripts\activate
$env:DATABASE_URL="sqlite:///./local.db"
uvicorn app.main:app --reload --port 8001
```

**Terminal 2 – juego:**

```
cd frontend
..\backend\.venv\Scripts\activate
$env:REACTOR_API_URL="http://127.0.0.1:8001"
python juego.py
```

### En el juego

- Crear una cuenta o iniciar sesión (los códigos de verificación aparecen en la Terminal 1).
- En el menú, **Jugar**.
- Moverse con las flechas o con el Arduino · **V**: ceremonia de victoria · **ESC**: volver al menú.

## Desde el celular (US-024)

El backend también sirve una versión web para celular: login, registro, verificación, recuperar
contraseña, Google y GitHub, menú, perfil y ranking.

1. Encender el backend para que acepte conexiones de otros dispositivos:
   ```
   cd backend
   .venv\Scripts\activate
   $env:DATABASE_URL="sqlite:///./local.db"
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. Buscar la IP de la computadora con `ipconfig` (línea "Dirección IPv4", por ejemplo `192.168.1.50`).
3. Con el celular conectado al **mismo WiFi**, abrir en el navegador: `http://192.168.1.50:8000/movil`
4. Si no carga, permitir Python en el Firewall de Windows (redes privadas).

En la computadora también se puede abrir en `http://localhost:8000/movil`.

## Con Docker (todo el sistema)

Levanta la base de datos PostgreSQL, el backend de cuentas y el servidor de partidas:

```
copy .env.ejemplo .env
docker compose up --build
```

- Backend de cuentas: http://localhost:8000/docs
- Servidor de partidas: http://localhost:8002/docs

Para usar el juego con este backend: `$env:REACTOR_API_URL="http://127.0.0.1:8000"` antes de `python juego.py`.
Para apagar: `Ctrl + C` y luego `docker compose down`.

## Pruebas

```
cd backend
python -m pytest

cd ..\frontend
python -m pytest
```

## Estructura

| Carpeta | Contenido |
|---|---|
| `backend/` | API de cuentas, perfil y ranking (FastAPI + base de datos) |
| `frontend/` | Pantallas de login, registro, menú, perfil y ranking (Pygame) |
| `Logica_ReactorControl.py` y `assets/` | Juego de la arena: mapa, guardianes y ceremonia de victoria |
| `Logica-juego-backend/` | Servidor de partidas multijugador |
| `Botones_Reactor_control.ino` | Programa del control físico (Arduino) |
| `docs/` | Documentación (modelo de datos) |

La estrategia de ramas y el resto de la documentación están en la Wiki del proyecto en Azure DevOps.
