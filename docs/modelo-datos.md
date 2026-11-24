# Modelo de datos

**Motor:** PostgreSQL 16, en un contenedor de Docker para desarrollo (`docker-compose.yml`).
**Acceso desde el backend:** SQLAlchemy (ORM). Las tablas se definen en `backend/app/models.py`
y se crean automáticamente al arrancar el backend.

Basado en el diagrama de despliegue del ERS, que pide guardar: usuarios, credenciales,
partidas, puntajes, eventos, ranking y estadísticas.

## Diagrama entidad-relación

```mermaid
erDiagram
    JUGADORES ||--o{ PARTICIPACIONES : "juega"
    PARTIDAS  ||--o{ PARTICIPACIONES : "tiene"
    PARTIDAS  ||--o{ EVENTOS_PARTIDA : "registra"
    JUGADORES ||--o{ EVENTOS_PARTIDA : "provoca"
    JUGADORES ||--o{ RECORDS : "logra"
    PARTIDAS  |o--o{ RECORDS : "en"
    JUGADORES |o--o{ PARTIDAS : "gana"

    JUGADORES {
        int id PK
        string nombre_usuario UK
        string correo UK
        string contrasena_hash
        string proveedor
        bool correo_verificado
        datetime fecha_registro
        int puntos_totales
        int victorias
        int partidas_jugadas
    }
    PARTIDAS {
        int id PK
        string escenario
        string estado
        int puntuacion_objetivo
        int duracion_segundos
        datetime fecha_inicio
        datetime fecha_fin
        int ganador_id FK
    }
    PARTICIPACIONES {
        int id PK
        int partida_id FK
        int jugador_id FK
        int puntos
        int posicion
    }
    EVENTOS_PARTIDA {
        int id PK
        int partida_id FK
        int jugador_id FK
        string tipo
        int puntos
        datetime fecha
    }
    RECORDS {
        int id PK
        int jugador_id FK
        int partida_id FK
        string tipo
        int valor
        datetime fecha
    }
```

## Tablas

| Tabla | Qué guarda | Lo pide |
|---|---|---|
| `jugadores` | Usuario, correo, contraseña cifrada, proveedor de login y estadísticas acumuladas | Usuarios, credenciales, estadísticas · RN-01, RN-02, RNF-04 |
| `partidas` | Escenario, estado (`en_espera`, `en_curso`, `finalizada`), tiempos y ganador | Partidas · US-007, US-019 |
| `participaciones` | Puntos y posición final de cada jugador en cada partida | Puntajes · US-020 |
| `eventos_partida` | Lo que ocurre en una partida: extracciones, terminales, penalizaciones | Eventos · US-009, US-010, US-014 |
| `records` | Récords históricos por jugador | Récords · US-023 |
| `cuentas_sociales` | Une a un jugador con su cuenta de Google o GitHub (id que da el proveedor) | Login con redes sociales · US-002 |
| `inicios_sociales` | Inicios de sesión con Google/GitHub en proceso (vencen a los 10 min) | Login con redes sociales · US-002 |

## Decisiones

- **El ranking no tiene tabla propia.** Se calcula sumando `participaciones.puntos` por jugador
  (o usando `jugadores.puntos_totales`), así nunca queda desactualizado.
- **Correo y usuario únicos** con restricciones `UNIQUE` en la base de datos, no solo validación en código.
- **`contrasena_hash` puede estar vacía** para cuentas creadas con Google, GitHub, etc. (US-002).
- **Las redes sociales van en una tabla aparte** (`cuentas_sociales`) y no como columnas de `jugadores`:
  así un jugador puede tener Google y GitHub a la vez, y las bases de datos que ya existían no
  necesitan cambios (las tablas nuevas se crean solas al arrancar el backend).
- **Se guarda el id del proveedor, no solo el correo**, porque el correo de Google/GitHub puede cambiar.
- **Una sola base de datos en el Sprint 2.** La arquitectura lógica del ERS propone bases regionales
  (América y Europa) con balance de carga; eso queda como arquitectura ideal y no se implementa por ahora.
- **Pruebas con SQLite en memoria**, para que corran sin Docker en cualquier compu y en el pipeline de CI.