"""Las pruebas corren sin abrir ventanas (modo "dummy" de Pygame) y sin backend."""
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture
def ventana():
    pygame.init()
    yield pygame.display.set_mode((900, 700))
    pygame.quit()
