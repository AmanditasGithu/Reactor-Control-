"""Piezas visuales reutilizables: colores, campos de texto y botones."""
import pygame

# Colores del juego (los mismos de la ceremonia de victoria)
FONDO = (20, 25, 35)
PANEL = (40, 45, 60)
DORADO = (255, 215, 0)
CIAN = (0, 220, 200)
BLANCO = (255, 255, 255)
GRIS = (150, 155, 170)
ROJO = (255, 90, 90)
VERDE = (90, 220, 120)


class CampoTexto:
    """Caja donde el jugador escribe. Con `oculto=True` muestra puntos (para contraseñas)."""

    def __init__(self, x, y, ancho, etiqueta, oculto=False, largo_maximo=72):
        self.rect = pygame.Rect(x, y, ancho, 40)
        self.etiqueta = etiqueta
        self.oculto = oculto
        self.largo_maximo = largo_maximo
        self.texto = ""
        self.activo = False

    def manejar_evento(self, evento) -> None:
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self.activo = self.rect.collidepoint(evento.pos)
        elif evento.type == pygame.KEYDOWN and self.activo:
            if evento.key == pygame.K_BACKSPACE:
                self.texto = self.texto[:-1]
            elif evento.key in (pygame.K_RETURN, pygame.K_TAB, pygame.K_ESCAPE):
                pass  # estas teclas las maneja la pantalla
            elif evento.unicode and evento.unicode.isprintable():
                if len(self.texto) < self.largo_maximo:
                    self.texto += evento.unicode

    def dibujar(self, superficie, fuente, fuente_etiqueta) -> None:
        etiqueta = fuente_etiqueta.render(self.etiqueta, True, GRIS)
        superficie.blit(etiqueta, (self.rect.x, self.rect.y - 24))

        pygame.draw.rect(superficie, PANEL, self.rect, border_radius=5)
        pygame.draw.rect(superficie, CIAN if self.activo else GRIS, self.rect, 2, border_radius=5)

        visible = "•" * len(self.texto) if self.oculto else self.texto
        texto = fuente.render(visible, True, BLANCO)
        # Si el texto no cabe, se muestra solo el final
        recorte = max(0, texto.get_width() - (self.rect.width - 20))
        superficie.blit(texto, (self.rect.x + 10, self.rect.y + 9), (recorte, 0, self.rect.width - 20, 30))

        if self.activo and pygame.time.get_ticks() % 1000 < 500:  # cursor parpadeante
            x_cursor = self.rect.x + 10 + min(texto.get_width(), self.rect.width - 20) + 2
            pygame.draw.line(superficie, BLANCO, (x_cursor, self.rect.y + 9), (x_cursor, self.rect.y + 31), 2)


class Boton:
    """Botón con texto que se ilumina cuando el mouse pasa por encima."""

    def __init__(self, x, y, ancho, texto, principal=True):
        self.rect = pygame.Rect(x, y, ancho, 44)
        self.texto = texto
        self.principal = principal

    def fue_presionado(self, evento) -> bool:
        return (
            evento.type == pygame.MOUSEBUTTONDOWN
            and evento.button == 1
            and self.rect.collidepoint(evento.pos)
        )

    def dibujar(self, superficie, fuente) -> None:
        encima = self.rect.collidepoint(pygame.mouse.get_pos())
        if self.principal:
            pygame.draw.rect(superficie, DORADO if encima else (220, 185, 0), self.rect, border_radius=5)
            color_texto = FONDO
        else:
            pygame.draw.rect(superficie, CIAN if encima else GRIS, self.rect, 2, border_radius=5)
            color_texto = CIAN if encima else GRIS
        texto = fuente.render(self.texto, True, color_texto)
        superficie.blit(texto, texto.get_rect(center=self.rect.center))
