# Frontend – Control del Reactor (Pygame)

Pantallas del juego hechas con **pygame-ce**. Se importa igual que pygame (`import pygame`).

## Archivos

```
frontend/
├── cliente_api.py        ← habla con el backend (registro, login)
├── componentes.py        ← colores, campos de texto y botones
├── pantallas_cuentas.py  ← pantallas de login (US-004) y registro (US-001)
└── tests/                ← pruebas automáticas
```

## Instalar (una vez)

Con el entorno virtual del backend activo, desde la carpeta `frontend`:

```
pip install -r requirements.txt
```

Si antes instalaste `pygame` (no `-ce`), quitalo primero: `pip uninstall pygame`.

## Probar las pantallas

1. Encender el backend en una terminal (ver `backend/README.md`).
2. En otra terminal, desde `frontend`: `python pantallas_cuentas.py`

## Usarlas desde el juego

```python
from pantallas_cuentas import ejecutar_pantallas_cuentas

cliente, jugador = ejecutar_pantallas_cuentas(ventana)
# jugador["nombre_usuario"] -> quién inició sesión
# cliente.token             -> pase de sesión para el backend
```

## Pruebas

Desde `frontend`: `pytest`. No necesitan el backend ni abren ventanas.
