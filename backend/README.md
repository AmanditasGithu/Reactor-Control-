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
## Login con Google y GitHub (US-002)

Como el juego es de escritorio, el login con redes sociales pasa por el navegador:

1. El jugador toca **Entrar con Google** (o GitHub) y el juego abre el navegador.
2. El jugador inicia sesión allá. Google/GitHub lo mandan de vuelta a
   `/api/auth/social/<proveedor>/callback` y el backend busca o crea su cuenta.
3. Mientras tanto, el juego pregunta cada 2 segundos a `/api/auth/social/revisar`
   y, cuando el jugador termina, recibe el token igual que en el login normal.

Reglas:

- Solo entra si Google/GitHub confirman que el correo está **verificado**.
- Si ya existe una cuenta con ese correo, se une a la red social. Si ese correo ya estaba
  verificado, la contraseña sigue sirviendo; si no, se borra (podría haberla puesto otra persona).
- Si es nuevo, se crea sin contraseña y con un nombre de usuario sacado de su nombre
  (`José Pérez` → `Jose_Perez`; si está ocupado, `Jose_Perez2`).
- Los client secret los conoce solo el backend; el juego nunca los ve.

### Configurarlo (una vez por compu)

Cada proveedor se activa solo cuando tiene su client id y su client secret. Si faltan,
el botón muestra "todavía no está configurado" y lo demás sigue funcionando.

**GitHub** (el más rápido):

1. GitHub → *Settings* → *Developer settings* → *OAuth Apps* → **New OAuth App**.
2. *Homepage URL*: `http://localhost:8000`
3. *Authorization callback URL*: `http://localhost:8000/api/auth/social/github/callback`
4. Copiar el **Client ID** y tocar **Generate a new client secret**.

**Google**:

1. Entrar a [console.cloud.google.com](https://console.cloud.google.com) y crear un proyecto.
2. Configurar la pantalla de consentimiento de OAuth (tipo *External*). Mientras esté en
   modo de prueba, agregar los correos del equipo como *usuarios de prueba*.
3. Crear un **ID de cliente de OAuth** de tipo **Aplicación web**, con este
   *URI de redireccionamiento autorizado*: `http://localhost:8000/api/auth/social/google/callback`
4. Copiar el **ID de cliente** y el **secreto del cliente**.

**Poner las claves:**

- Con Docker: copiar `.env.ejemplo` (en la raíz del repo) como `.env`, llenarlo y correr
  `docker compose up --build`. Docker lee el `.env` solo.
- Sin Docker (PowerShell), antes de `uvicorn`:

  ```
  $env:GITHUB_CLIENT_ID="..."
  $env:GITHUB_CLIENT_SECRET="..."
  ```

> ⚠️ El `.env` nunca se sube a GitHub (ya está en `.gitignore`). Si un secreto se sube por
> error, hay que generar uno nuevo en Google/GitHub.

Si el backend se publica en otra dirección (por ejemplo en la nube), se cambia `URL_BACKEND`
y se agrega la nueva dirección de callback en Google y en GitHub.
