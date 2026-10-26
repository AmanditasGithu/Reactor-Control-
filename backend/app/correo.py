"""Envío de correos SIMULADO.

Todavía no hay un servidor de correo real, así que el "correo" se escribe en la
terminal donde corre el backend. Cuando haya uno, solo se cambia esta función.
"""


def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> None:
    print("\n" + "=" * 50, flush=True)
    print("CORREO SIMULADO", flush=True)
    print(f"Para:   {destinatario}", flush=True)
    print(f"Asunto: {asunto}", flush=True)
    print(cuerpo, flush=True)
    print("=" * 50 + "\n", flush=True)
