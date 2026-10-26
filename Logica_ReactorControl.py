import pygame
import sys
import math #para los guardianes
import os #Para las imagenes

pygame.init()

#Prototipo de usuario jugador (no prestarle tanta atención por fis)

ANCHO, ALTO = 800,600
ventana = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Prueba - User")
#Colores del los prototipos de los bichos
BLANCO = (255,255,255)
AZUL = (0,120,255)
GRIS = (100,100,100)
ROJO= (255,50,50)
#Clase para los guardianes 
class Guardian(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        #Actualice tambien el tamano de un guardian de la celda
        self.rect = pygame.Rect(
    x, y,
    TAMANO_CELDA,
    TAMANO_CELDA
)
        self.velocidad_base = 1.5  # Ligeramente más lento que el jugador
        self.color = (128, 0, 128) #Moradito 
    def actualizar(self, jugador):
        distancia_x = jugador.rect.centerx - self.rect.centerx #Comando pygame para calcular la distancia con el jugador 
        distancia_y = jugador.rect.centery - self.rect.centery
        distancia = math.hypot(distancia_x, distancia_y)
        rango_deteccion = 250 #Por ejemplo, si el jugador esta a menos de estos 250 pixeles lo empieza a perseguir el guardian

        if 0 < distancia < rango_deteccion: #Esta logica es la mas acertada que encontre para que el guardian persiga al jugador 
            # Persecucion en X
            if distancia_x != 0:
                if distancia_x > 0:
                    self.rect.x += self.velocidad_base
                else:
                    self.rect.x -= self.velocidad_base
                    
            # Persecucion en Y
            if distancia_y != 0:
                if distancia_y > 0:
                    self.rect.y += self.velocidad_base
                else:
                    self.rect.y -= self.velocidad_base
    def dibujar(self,superficie): 
        if USAR_IMAGENES:
            superficie.blit(img_guardian,self.rect) #Para que me use la imagen del guardian
        else:
            pygame.draw.rect(superficie,self.color,self.rect)
#Clase Jugador 
class Jugador(pygame.sprite.Sprite): #constructor 
    def __init__(self, x, y):
        super().__init__()
        #Actualice esto para que el jugador tuviera el tamano de una celda a ver si acaso
        self.rect = pygame.Rect(
    x, y,
    TAMANO_CELDA,
    TAMANO_CELDA
)
        self.velocidad_base = 5
        self.velocidad_actual = self.velocidad_base
        self.color = AZUL

    def Mover(self, teclas, obstaculos):
        mov_x = 0 #MOVIMIENTO VERTICAL
        if teclas[pygame.K_LEFT]: #Comando de Pygame para movimiento horizontal
            mov_x = -self.velocidad_actual #como desplazamiento en coordenadas
        if teclas[pygame.K_RIGHT]:
            mov_x = self.velocidad_actual

        self.rect.x += mov_x
        for obs in obstaculos:
            if obs.tipo == "barrera" and self.rect.colliderect(obs.rect): #Comando para choque con obstaculos
                if mov_x > 0: 
                    self.rect.right = obs.rect.left
                if mov_x < 0: 
                    self.rect.left = obs.rect.right

        mov_y = 0 #MOVIMIENTO VERTICAL
        if teclas[pygame.K_UP]: #Comando de Pygame para movimiento vertical
                mov_y = -self.velocidad_actual 
        if teclas[pygame.K_DOWN]:
                mov_y = self.velocidad_actual
        self.rect.y += mov_y
        #A continuacion proceso a hacer la accion de colision
        for obs in obstaculos:
             if obs.tipo == "barrera" and self.rect.colliderect(obs.rect): #Comando pygame para golpear con objetos 
                  if mov_y>0: 
                      self.rect.bottom = obs.rect.top
                  if mov_y<0: 
                      self.rect.top = obs.rect.bottom

    def dibujar(self,superficie): #Para que use la imagen del guardian
         if USAR_IMAGENES:
             superficie.blit(img_jugador,self.rect)
         else:
            pygame.draw.rect(superficie, self.color, self.rect)
#Clase de obstaculos y trampillas
class Obstaculo:
    def __init__(self, x, y, ancho, alto, tipo):
        self.rect = pygame.Rect(x,y, ancho, alto)
        self.tipo = tipo # Con esto quiero hacer la diferencia entre trampa o barrera

        if self.tipo == "barrera":
         self.color = GRIS
        elif self.tipo == "trampa":
            self.color = ROJO
    def dibujar(self, superficie): #Lo cambie para que me tirara las imagenes 
         if USAR_IMAGENES:
             if self.tipo == "barrera":
                 superficie.blit(img_pared, self.rect)
             elif self.tipo == "trampa":
                 superficie.blit(img_trampa, self.rect)
         else:
             pygame.draw.rect(superficie, self.color, self.rect)




###Cuadricula#####
# '#' = Pared / Barrera
# ' ' = Pasillo libre
# 'T' = Trampa de velocidad
# 'R' = Zona del Reactor Central
# 'G' = Guardian

matriz_mapa = [
    "####################################",
    "#              T                   #",
    "#   ########   #   #############   #",
    "#          #   #   #               #",
    "#       T  #   #####   ####### #   #",
    "#   #                  #     # #   #",
    "#   ########   #########     # ### #",
    "#              #        G          #",
    "#   ############   R          #    #",
    "#       G           #          # T #",
    "# T ##################   ###########",
    "#              T               #   #",
    "####################################"
]

TAMANO_CELDA =20
obstaculos = []
guardianes = []
reactor = None

# Con este comando quiero detectar la resolución de la pantalla
info_pantalla = pygame.display.Info()
ANCHO_PANTALLA = info_pantalla.current_w
ALTO_PANTALLA = info_pantalla.current_h

# Dimensiones del mapa
COLUMNAS = max(len(fila) for fila in matriz_mapa)
FILAS = len(matriz_mapa)
#ENGAGE
ventana = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Control del Reactor")

ANCHO_PANTALLA, ALTO_PANTALLA = ventana.get_size()

# Este comando es para que el mapa no toque los bordes
MARGEN = 12

TAMANO_CELDA = min( #Con este comando lo que hago es calcular el tamano de las celdas para que todo entre
    (ANCHO_PANTALLA - 2 * MARGEN) // COLUMNAS,
    (ALTO_PANTALLA - 2 * MARGEN) // FILAS
)

# Con esto centro el mapa
ANCHO_MAPA = COLUMNAS * TAMANO_CELDA
ALTO_MAPA = FILAS * TAMANO_CELDA

OFFSET_X = (ANCHO_PANTALLA - ANCHO_MAPA) // 2
OFFSET_Y = (ALTO_PANTALLA - ALTO_MAPA) // 2

jugador = Jugador(
    OFFSET_X + TAMANO_CELDA,
    OFFSET_Y + TAMANO_CELDA
)
##Bloque para las imagenes##
CARPETA_ASSETS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets"
)

try:
    img_jugador = pygame.transform.scale(
        pygame.image.load(
            os.path.join(CARPETA_ASSETS, "Azulfrente.png")
        ).convert_alpha(),
        (TAMANO_CELDA, TAMANO_CELDA)
    )

    img_guardian = pygame.transform.scale(
        pygame.image.load(
            os.path.join(CARPETA_ASSETS, "Guardiandelante.png")
        ).convert_alpha(),
        (TAMANO_CELDA, TAMANO_CELDA)
    )

    img_piso = pygame.transform.scale(
        pygame.image.load(
            os.path.join(CARPETA_ASSETS, "piso.png")
        ).convert_alpha(),
        (TAMANO_CELDA, TAMANO_CELDA)
    )

    img_pared = pygame.transform.scale(
        pygame.image.load(
            os.path.join(CARPETA_ASSETS, "Paredfrente.png")
        ).convert_alpha(),
        (TAMANO_CELDA, TAMANO_CELDA)
    )

    img_trampa = pygame.transform.scale(
        pygame.image.load(
            os.path.join(CARPETA_ASSETS, "trampa.png")
        ).convert_alpha(),
        (TAMANO_CELDA, TAMANO_CELDA)
    )

    img_reactor = pygame.transform.scale(
        pygame.image.load(
            os.path.join(CARPETA_ASSETS, "Reactor.png")
        ).convert_alpha(),
        (TAMANO_CELDA, TAMANO_CELDA)
    )
    USAR_IMAGENES = True
    print("Imagenes cargadas correctamente")

except (pygame.error,FileNotFoundError) as e: #En caso de que no funcione que no me estropee todo y siga con menor resolucion
    print("Advertencia: No se pudieron cargar las imagenes. Se usan colores planos:", e)
    USAR_IMAGENES = False

def cargar_Mapa(matriz):
    global reactor

    obstaculos.clear()
    guardianes.clear()
    reactor = None

    for fila_idx, fila in enumerate(matriz):
        for col_idx, caracter in enumerate(fila):
          x = OFFSET_X + (col_idx * TAMANO_CELDA)
          y = OFFSET_Y + (fila_idx * TAMANO_CELDA)
          
          if caracter == "#":
                obstaculos.append(
                    Obstaculo(
                        x, y,
                        TAMANO_CELDA, TAMANO_CELDA,
                        "barrera"
                    )
                )

          elif caracter == "T":
                obstaculos.append(
                    Obstaculo(
                        x, y,
                        TAMANO_CELDA, TAMANO_CELDA,
                        "trampa"
                    )
                )

          elif caracter == "G":
                guardianes.append(Guardian(x, y))

          elif caracter == "R":
                reactor = pygame.Rect(
                    x, y,
                    TAMANO_CELDA, TAMANO_CELDA
                )


def dibujar_mapa(superficie, matriz):
    for fila_idx, fila in enumerate(matriz):
        for col_idx, caracter in enumerate(fila):
            x = OFFSET_X + col_idx * TAMANO_CELDA
            y = OFFSET_Y + fila_idx * TAMANO_CELDA

            celda_rect = pygame.Rect(
                x, y, TAMANO_CELDA, TAMANO_CELDA
            )

            if USAR_IMAGENES:
                superficie.blit(img_piso, celda_rect)

                #Elemento de la celda 
                if caracter == "#":
                    superficie.blit(img_pared, celda_rect)

                elif caracter == "T":
                    superficie.blit(img_trampa, celda_rect)

                elif caracter == "R":
                    superficie.blit(img_reactor, celda_rect)

            else:
                #Si no cargan las imagenes entonces vuelvo a los rectagulos 
                pygame.draw.rect(
                    superficie, (35, 40, 55), celda_rect
                )

                if caracter == "#":
                    pygame.draw.rect(superficie, GRIS, celda_rect)

                elif caracter == "T":
                    pygame.draw.rect(superficie, ROJO, celda_rect)

                elif caracter == "R":
                    pygame.draw.rect(
                        superficie, (0, 220, 200), celda_rect
                    )


            pygame.draw.rect(
                superficie,
                (65, 75, 90),
                celda_rect,
                1
            ) #Bordecillo ahi para la cuadricula 
            # Piso de cada celda
            pygame.draw.rect(
                superficie,
                (35, 40, 55),
                (x, y, TAMANO_CELDA, TAMANO_CELDA)
            )

            if caracter == "#":
                pygame.draw.rect(
                    superficie,
                    GRIS,
                    (x, y, TAMANO_CELDA, TAMANO_CELDA)
                )

            elif caracter == "T":
                pygame.draw.rect(
                    superficie,
                    ROJO,
                    (x, y, TAMANO_CELDA, TAMANO_CELDA)
                )

            elif caracter == "R":
                pygame.draw.rect(
                    superficie,
                    (0, 220, 200),
                    (x, y, TAMANO_CELDA, TAMANO_CELDA)
                )

            # Bordes 
            pygame.draw.rect(
                superficie,
                (65, 75, 90),
                (x, y, TAMANO_CELDA, TAMANO_CELDA),
                1
            )


cargar_Mapa(matriz_mapa)



#Comando de pygame para setear un timer 
reloj = pygame.time.Clock()
#prueba de la logica
while True:
    ventana.fill((20,25,35))
    
    # Manejo de eventos
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
    teclas = pygame.key.get_pressed()
    dibujar_mapa(ventana,matriz_mapa)

    #Verificar si el jugador esta pisando una trampa 
    en_trampa = False
    for obs in obstaculos:
        if obs.tipo == "trampa" and jugador.rect.colliderect(obs.rect):
            en_trampa = True
            break 
    #Si esta en la trampa le reduce velocidad, si no nada pasa
    if en_trampa:
        jugador.velocidad_actual = 2 #reducido en dos
    else:
        jugador.velocidad_actual = jugador.velocidad_base
    
    jugador.Mover(teclas, obstaculos)

    for guardian in guardianes:
        guardian.actualizar(jugador)
        guardian.dibujar(ventana)

    #Dibujar onstaculos
    for obs in obstaculos:
        obs.dibujar (ventana)
    jugador.dibujar(ventana)
    


    pygame.display.flip()
    reloj.tick(60)








        



