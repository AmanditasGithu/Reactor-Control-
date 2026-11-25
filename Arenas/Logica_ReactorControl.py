import pygame
import sys
import math #para los guardianes 
import os #Para las imagenes 
import serial
import time 
import random
from Adapter import AdaptadorEstadoBackend
from Eventos_Especiales import (
    FabricaEventosEscenario,
    EventoTransferenciaCeldasLab,
    EventoReduccionEnergiaMilitar,
)
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

### 2. CONFIGURACIÓN DE LA CONEXIÓN SERIAL (ARDUINO) ###
#'COM3' por el puerto al que esté conectado al Arduino MEGA
try:
    puerto_serial = serial.Serial('COM3', 115200, timeout=0.01)
    print("Control fisico de Arduino conectado exitosamente por puerto serial")
except:
    puerto_serial = None
    print("Aviso: No se detectó el Arduino en el puerto COM3. Se jugara solo con el teclado.")

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

    def Mover(self, teclas, comando_hardware, obstaculos):
        mov_x = 0 #MOVIMIENTO VERTICAL
        if teclas[pygame.K_LEFT] or comando_hardware == "IZQUIERDA": #Comando de Pygame para movimiento horizontal
            mov_x = -self.velocidad_actual #como desplazamiento en coordenadas
        if teclas[pygame.K_RIGHT] or comando_hardware == "DERECHA":
            mov_x = self.velocidad_actual

        self.rect.x += mov_x
        for obs in obstaculos:
            if obs.tipo == "barrera" and self.rect.colliderect(obs.rect): #Comando para choque con obstaculos
                if mov_x > 0: 
                    self.rect.right = obs.rect.left
                if mov_x < 0: 
                    self.rect.left = obs.rect.right

        mov_y = 0 #MOVIMIENTO VERTICAL
        if teclas[pygame.K_UP] or comando_hardware == "ARRIBA": #Comando de Pygame para movimiento vertical
                mov_y = -self.velocidad_actual 
        if teclas[pygame.K_DOWN] or comando_hardware == "ABAJO":
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
    def dibujar(self, superficie):  # Lo cambie para que me tirara las imagenes
        if USAR_IMAGENES:
            if self.tipo == "barrera":
                if escenario_actual == "laboratorio_subterraneo" and USAR_IMAGENES_LAB:
                    superficie.blit(img_pared_lab, self.rect)
                elif escenario_actual == "complejo_militar" and USAR_IMAGENES_MILITAR:
                    superficie.blit(img_pared_militar, self.rect)
                else:
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
    "#          #   #   #             E #",
    "#       T  #   #####   ####### #   #",
    "#   #                  #     # #   #",
    "#   ########   #########     # ### #",
    "#                       G          #",
    "#   ############   R               #",
    "#       G           #          # T #",
    "# T ##################   ###########",
    "# E             T               #  #",
    "####################################"
]

matriz_laboratorio_subterraneo = [
    "####################################",
    "# C        #       T    G  #     C #",
    "#   ####   #   ###########   ###   #",
    "#      #       #         #     E   #",
    "#  T   #####   #     #       ###   #",
    "#      #       #    R              #",
    "#  C   #   #####   ###   #####   C #",
    "#      #       G             #     #",
    "#  #####   #########   #######   T #",
    "#          #       #               #",
    "#  E   #####   T   #   #########   #",
    "#      C                       C   #",
    "####################################"
]
MAPAS_ESCENARIOS = {
    "planta_industrial": matriz_mapa,
    "laboratorio_subterraneo": matriz_laboratorio_subterraneo,
}

matriz_complejo_militar = [
    "####################################",
    "#      C    #       T          G   #",
    "# E  ####   #   ###########   ###  #",
    "#              #    E              #",
    "#  T    ####         #       ###   #",
    "#      C       #    R         C    #",
    "#  ####    ###  G      ###   ##### #",
    "#              #         #         #",
    "#  G   #####   #######   #####   G #",
    "#                  G       T       #",
    "#  E   #####   T         ######### #",
    "#      C             #        E    #",
    "####################################"
]

MAPAS_ESCENARIOS = {
    "planta_industrial": matriz_mapa,
    "laboratorio_subterraneo": matriz_laboratorio_subterraneo,
    "complejo_militar": matriz_complejo_militar,
}

TAMANO_CELDA =20
obstaculos = []
celdas_energia = []
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

adaptador = AdaptadorEstadoBackend(OFFSET_X, OFFSET_Y, TAMANO_CELDA)

jugador = Jugador(
    OFFSET_X + TAMANO_CELDA,
    OFFSET_Y + TAMANO_CELDA
)

def cargar_sprite_ajustado(ruta_imagen, tamano):
    img = pygame.image.load(ruta_imagen).convert_alpha()
    area_visible = img.get_bounding_rect()
    if area_visible.width > 0 and area_visible.height > 0:
        img = img.subsurface(area_visible).copy()
    return pygame.transform.smoothscale(img, (tamano, tamano))

##Bloque para las imagenes##
CARPETA_ASSETS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets"
)

USAR_IMAGENES = False
USAR_IMAGENES_LAB = False
USAR_IMAGEN_CELDA = False
USAR_IMAGEN_TERMINAL = False
USAR_IMAGENES_RIVALES = False
USAR_IMAGENES_MILITAR = False

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

    img_pared_lab = cargar_sprite_ajustado(
        os.path.join(CARPETA_ASSETS, "paredlab.png"),
        TAMANO_CELDA,
    )

    img_piso_lab = cargar_sprite_ajustado(
        os.path.join(CARPETA_ASSETS, "pisolab.png"),
        TAMANO_CELDA,
    )

    img_reactor_lab = cargar_sprite_ajustado(
        os.path.join(CARPETA_ASSETS, "reactorlab.png"),
        TAMANO_CELDA,
    )

    img_celda_lab = cargar_sprite_ajustado(
        os.path.join(CARPETA_ASSETS, "Celdalab.png"),
        TAMANO_CELDA,
    )
    USAR_IMAGENES_LAB = True

    img_celda = cargar_sprite_ajustado(
        os.path.join(CARPETA_ASSETS, "Celdalab.png"),
        TAMANO_CELDA,
    )
    USAR_IMAGEN_CELDA = True

    img_terminal = cargar_sprite_ajustado(
        os.path.join(CARPETA_ASSETS, "Celdalab.png"),  # o el sprite que uses para terminales/celdas
        TAMANO_CELDA,
    )
    USAR_IMAGEN_TERMINAL = True

    img_rival_naranja = cargar_sprite_ajustado(
        os.path.join(CARPETA_ASSETS, "Naranjafrente.png"),
        TAMANO_CELDA,
    )

    img_rival_verde = cargar_sprite_ajustado(
        os.path.join(CARPETA_ASSETS, "Verdeadelante.png"),
        TAMANO_CELDA,
    )
    USAR_IMAGENES_RIVALES = True

    img_pared_militar = cargar_sprite_ajustado(
    os.path.join(CARPETA_ASSETS, "paredmilitar.png"),
    TAMANO_CELDA,
)

    img_piso_militar = cargar_sprite_ajustado(
        os.path.join(CARPETA_ASSETS, "pisomilitar.png"),
        TAMANO_CELDA,
    )

    img_reactor_militar = cargar_sprite_ajustado(
        os.path.join(CARPETA_ASSETS, "reactormilitar.png"),
        TAMANO_CELDA,
    )

    img_celda_militar = cargar_sprite_ajustado(
        os.path.join(CARPETA_ASSETS, "celdamilitar.png"),
        TAMANO_CELDA,
    )
    USAR_IMAGENES_MILITAR = True

    USAR_IMAGENES = True
    print("Imagenes cargadas correctamente")

except (pygame.error, FileNotFoundError) as e:
    print("Advertencia: No se pudieron cargar las imagenes. Se usan colores planos:", e)
    USAR_IMAGENES = False
    USAR_IMAGENES_LAB = False
    USAR_IMAGEN_CELDA = False
    USAR_IMAGEN_TERMINAL = False
    USAR_IMAGENES_RIVALES = False
    USAR_IMAGENES_MILITAR = False

###Imagenes de pantalla de victoria##
try:
    img_fondo_victoria = pygame.transform.scale(
        pygame.image.load(
            os.path.join(CARPETA_ASSETS, "Fondovictoria.png")
        ).convert(),
        (ANCHO_PANTALLA, ALTO_PANTALLA)
    )

    # Sprites de ganadores
    img_azul_victoria = pygame.image.load(
        os.path.join(CARPETA_ASSETS, "Azulvictoria.png")
    ).convert_alpha()

    img_naranja_victoria = pygame.image.load(
        os.path.join(CARPETA_ASSETS, "Naranjavictoria.png")
    ).convert_alpha()

    img_verde_victoria = pygame.image.load(
        os.path.join(CARPETA_ASSETS, "Verdevictoria.png")
    ).convert_alpha()

    # Sprites de derrotas
    img_azul_derrota = pygame.image.load(
        os.path.join(CARPETA_ASSETS, "Azulderrota.png")
    ).convert_alpha()

    img_naranja_derrota = pygame.image.load(
        os.path.join(CARPETA_ASSETS, "Naranjaderrota.png")
    ).convert_alpha()

    img_verde_derrota = pygame.image.load(
        os.path.join(CARPETA_ASSETS, "Verdederrota.png")
    ).convert_alpha()

    USAR_VICTORIA_VISUAL = True
    print("Imagenes de victoria cargadas correctamente")

except (pygame.error, FileNotFoundError) as e:
    print("Error cargando imagenes de victoria:", e)
    USAR_VICTORIA_VISUAL = False


coords_reactor = (5, 5)
coords_terminales = []


def cargar_Mapa(matriz):
    global reactor, coords_reactor, coords_terminales

    obstaculos.clear()
    celdas_energia.clear()
    guardianes.clear()
    reactor = None
    coords_terminales = []

    for fila_idx, fila in enumerate(matriz):
        for col_idx, caracter in enumerate(fila):
          x = OFFSET_X + (col_idx * TAMANO_CELDA)
          y = OFFSET_Y + (fila_idx * TAMANO_CELDA)

          if caracter == "#":
                obstaculos.append(Obstaculo(x, y, TAMANO_CELDA, TAMANO_CELDA, "barrera"))
          elif caracter == "T":
                obstaculos.append(Obstaculo(x, y, TAMANO_CELDA, TAMANO_CELDA, "trampa"))
          elif caracter == "G":
                guardianes.append(Guardian(x, y))
          elif caracter == "R":
               reactor = pygame.Rect(x, y, TAMANO_CELDA, TAMANO_CELDA)
               coords_reactor = (col_idx, fila_idx)
          elif caracter == "E":
                coords_terminales.append((col_idx, fila_idx))
          elif caracter == "C":
                celdas_energia.append(pygame.Rect(x, y, TAMANO_CELDA, TAMANO_CELDA))
                    

def dibujar_mapa(superficie, matriz):
    es_lab = escenario_actual == "laboratorio_subterraneo" and USAR_IMAGENES_LAB
    es_militar = escenario_actual == "complejo_militar" and USAR_IMAGENES_MILITAR

    for fila_idx, fila in enumerate(matriz):
        for col_idx, caracter in enumerate(fila):
            x = OFFSET_X + col_idx * TAMANO_CELDA
            y = OFFSET_Y + fila_idx * TAMANO_CELDA

            celda_rect = pygame.Rect(x, y, TAMANO_CELDA, TAMANO_CELDA)

            if USAR_IMAGENES:
                if es_lab:
                    piso_actual = img_piso_lab
                    pared_actual = img_pared_lab
                    reactor_actual = img_reactor_lab
                elif es_militar:
                    piso_actual = img_piso_militar
                    pared_actual = img_pared_militar
                    reactor_actual = img_reactor_militar
                else:
                    piso_actual = img_piso
                    pared_actual = img_pared
                    reactor_actual = img_reactor

                superficie.blit(piso_actual, celda_rect)

                if caracter == "#":
                    superficie.blit(pared_actual, celda_rect)
                elif caracter == "T":
                    superficie.blit(img_trampa, celda_rect)
                elif caracter == "R":
                    superficie.blit(reactor_actual, celda_rect)

            if not es_lab and not es_militar:
                pygame.draw.rect(superficie, (65, 75, 90), celda_rect, 1)

    for celda_rect_item in celdas_energia:
        if es_lab:
            superficie.blit(img_celda_lab, celda_rect_item)
        elif es_militar:
            superficie.blit(img_celda_militar, celda_rect_item)
        elif USAR_IMAGEN_CELDA:
            superficie.blit(img_celda, celda_rect_item)
        else:
            pygame.draw.rect(superficie, (0, 225, 255), celda_rect_item, border_radius=4)
            pygame.draw.rect(superficie, (255, 255, 255), celda_rect_item, 2, border_radius=4)

def seleccionar_escenario(nombre_escenario):
    global escenario_actual, matriz_activa, partida, jugador_logico, evento_escenario
    global vida_jugador, ataques_sufridos, energia_extraida, celdas_obtenidas, motivo_game_over

    clave = (nombre_escenario or "").strip().lower()
    if clave not in MAPAS_ESCENARIOS:
        clave = "planta_industrial"

    escenario_actual = clave
    matriz_activa = MAPAS_ESCENARIOS[escenario_actual]

    # Aqui me reinicia la partida para que no quede lo del mapa anterior 
    vida_jugador = vida_maxima
    ataques_sufridos = 0
    energia_extraida = 0
    celdas_obtenidas = 0
    motivo_game_over = None

    jugador.rect.topleft = (OFFSET_X + TAMANO_CELDA, OFFSET_Y + TAMANO_CELDA)
    jugador.velocidad_actual = jugador.velocidad_base

    cargar_Mapa(matriz_activa)
    partida, jugador_logico = adaptador.crear_partida_integrada(
        coords_reactor[0], coords_reactor[1], coords_terminales
    )
    evento_escenario = FabricaEventosEscenario.crear_evento(escenario_actual)
    print(f"Escenario cargado: {escenario_actual}")


##Esto es para la ceremonia de victoria con confetti y eso
class ParticulaConfeti:
    def __init__(self, ancho, alto):
        self.ancho = ancho
        self.alto = alto
        self.colores = [
            (255, 215, 0),   # corado
            (0, 225, 255),   # verde agua
            (80, 255, 130),  # verde
            (255, 80, 120),  # rosita
            (255, 150, 40),  # anaranjado
        ]
        self.reiniciar(aleatorio_y=True)

    def reiniciar(self, aleatorio_y=False):
        self.x = random.uniform(0, self.ancho)
        self.y = random.uniform(-self.alto, 0) if aleatorio_y else random.uniform(-40, -10)
        self.vel_y = random.uniform(2.0, 5.5)
        self.vel_x = random.uniform(-1.5, 1.5)
        self.tam_w = random.randint(7, 13)
        self.tam_h = random.randint(5, 10)
        self.color = random.choice(self.colores)
        self.fase = random.uniform(0, math.pi * 2)

    def actualizar(self, ahora):
        self.y += self.vel_y
        self.x += self.vel_x + math.sin(ahora * 5 + self.fase) * 0.8
        if self.y > self.alto + 20 or self.x < -30 or self.x > self.ancho + 30:
            self.reiniciar(aleatorio_y=False)

    def dibujar(self, superficie):
        pulso_alto = max(2, int(abs(math.cos(self.y * 0.04 + self.fase)) * self.tam_h))
        rect = pygame.Rect(int(self.x), int(self.y), self.tam_w, pulso_alto)
        pygame.draw.rect(superficie, self.color, rect, border_radius=2)


confeti_victoria = [ParticulaConfeti(ANCHO_PANTALLA, ALTO_PANTALLA) for _ in range(90)]



def ceremonia_victoria(superficie,ganador,datos_jugadores, ahora=0.0):
    if USAR_VICTORIA_VISUAL:
        superficie.blit(img_fondo_victoria, (0, 0))
    else:
        superficie.fill((15, 20, 30))
    #Esto es para centrar al ganador en el medio 
    centro_x = ANCHO_PANTALLA // 2
    centro_y = ALTO_PANTALLA // 2

    if USAR_VICTORIA_VISUAL:
        if ganador == "Azul":
            superficie.blit(
                pygame.transform.scale(img_naranja_derrota, (240, 360)),
                (centro_x - 390, centro_y - 100)
            )
            superficie.blit(
                pygame.transform.scale(img_verde_derrota, (240, 360)),
                (centro_x + 150, centro_y - 100)
            )
            superficie.blit(
                pygame.transform.scale(img_azul_victoria, (360, 480)),
                (centro_x - 180, centro_y - 150)
            )

        elif ganador == "Naranja":
            superficie.blit(
                pygame.transform.scale(img_azul_derrota, (240, 360)),
                (centro_x - 390, centro_y - 100)
            )
            superficie.blit(
                pygame.transform.scale(img_verde_derrota, (240, 360)),
                (centro_x + 150, centro_y - 100)
            )
            superficie.blit(
                pygame.transform.scale(img_naranja_victoria, (360, 480)),
                (centro_x - 180, centro_y - 150)
            )

        else:  #Gana el verde
            superficie.blit(
                pygame.transform.scale(img_azul_derrota, (240, 360)),
                (centro_x - 390, centro_y - 100)
            )
            superficie.blit(
                pygame.transform.scale(img_naranja_derrota, (240, 360)),
                (centro_x + 150, centro_y - 100)
            )
            superficie.blit(
                pygame.transform.scale(img_verde_victoria, (360, 480)),
                (centro_x - 180, centro_y - 150)
            )

    for p in confeti_victoria:
        p.actualizar(ahora)
        p.dibujar(superficie)


    #Estas son las barras de puntaje programadas
    fuente_hud = pygame.font.SysFont("Arial", 20, bold=True)
    ancho_barra = min(250, (ANCHO_PANTALLA - 80) // 3)
    alto_barra = 35
    separacion = (ANCHO_PANTALLA - 3 * ancho_barra) // 4
    
    #Se dibujan las 3 barras por jugador para ver los stats
    rects_jugadores = []
    for i, jg in enumerate(datos_jugadores):
        pos_x = separacion + i * (ancho_barra + separacion)
        pos_y = 30

        rect_barra = pygame.Rect(pos_x, pos_y, ancho_barra, alto_barra)
        rects_jugadores.append((rect_barra,jg))

        #Con esto hago el color del fondo de la barra de stats
        pygame.draw.rect(superficie, (40, 45, 60), rect_barra, border_radius=5)
        pygame.draw.rect(superficie, (255, 215, 0), rect_barra, 2, border_radius=5) # Borde dorado arcade

        #Texto con el nombre y los puntos 
        texto_barra = fuente_hud.render(f"{jg['nombre']}: {jg['puntos']} pts", True, (255, 255, 255))
        superficie.blit(texto_barra, (pos_x + 15, pos_y + 7))

    pos_mouse = pygame.mouse.get_pos() #Este es el comando de Pygame para que cuando le ponga el cursos encima me diga especificaciones
    for rect_barra, jg in rects_jugadores:
        if rect_barra.collidepoint(pos_mouse):

            #Dibujo las estadisticas flotantes 
            tooltip_rect = pygame.Rect(pos_mouse[0], pos_mouse[1] + 15, 220, 125)
            pygame.draw.rect(superficie, (10, 15, 25), tooltip_rect)
            pygame.draw.rect(superficie, (0, 220, 200), tooltip_rect, 2)

            fuente_tip = pygame.font.SysFont("Arial", 14)
            t1 = fuente_tip.render(f"Jugador: {jg['nombre']}", True, (255, 255, 255))
            t2 = fuente_tip.render(f"Energía Extraída: {jg.get('energia', 0)}", True, (200, 200, 200))
            t3 = fuente_tip.render(f"Celdas de Energía: {jg.get('celdas', 0)}", True, (200, 200, 200))
            t4 = fuente_tip.render(f"Golpes Recibidos: {jg.get('golpes_sufridos', 0)}", True, (200, 200, 200))
            t5 = fuente_tip.render(f"Vida Final: {jg.get('vida', 0)}", True, (200, 200, 200))

            superficie.blit(t1, (tooltip_rect.x + 10, tooltip_rect.y + 8))
            superficie.blit(t2, (tooltip_rect.x + 10, tooltip_rect.y + 28))
            superficie.blit(t3, (tooltip_rect.x + 10, tooltip_rect.y + 48))
            superficie.blit(t4, (tooltip_rect.x + 10, tooltip_rect.y + 68))
            superficie.blit(t5, (tooltip_rect.x + 10, tooltip_rect.y + 88))

def dibujar_barra_inferior_deltarune(
    superficie,
    nombre_jugador,
    ataques,
    max_ataques,
    energia,
    max_energia,
    celdas,
    max_celdas,
):
    alto_panel = 78
    margen_x = 24
    ancho_panel = ANCHO_PANTALLA - (margen_x * 2)
    y_panel = ALTO_PANTALLA - alto_panel - 10

    panel_rect = pygame.Rect(margen_x, y_panel, ancho_panel, alto_panel)
    pygame.draw.rect(superficie, (12, 14, 24), panel_rect)
    pygame.draw.rect(superficie, (240, 240, 255), panel_rect, 3)

##Aqui es lo de la imagen del jugador 
    tam_retrato = 54
    retrato_rect = pygame.Rect(panel_rect.x + 14, panel_rect.y + 12, tam_retrato, tam_retrato)
    if USAR_IMAGENES:
        retrato_img = pygame.transform.scale(img_jugador, (tam_retrato, tam_retrato))
        superficie.blit(retrato_img, retrato_rect)
    else:
        pygame.draw.rect(superficie, (0, 200, 255), retrato_rect)
    pygame.draw.rect(superficie, (255, 255, 255), retrato_rect, 2)

    fuente_nombre = pygame.font.SysFont(["Courier New", "Consolas", "Arial Black"], 22, bold=True)
    fuente_stat = pygame.font.SysFont(["Courier New", "Consolas", "Arial"], 14, bold=True)

    txt_nombre = fuente_nombre.render(nombre_jugador.upper(), True, (255, 255, 255))
    superficie.blit(txt_nombre, (retrato_rect.right + 14, panel_rect.y + 24))

    ##Barras horizontales 
    stats = [
        ("ATAQUES", ataques, max_ataques, (255, 70, 110)),
        ("ENERGIA", energia, max_energia, (0, 225, 255)),
        ("CELDAS", celdas, max_celdas, (80, 255, 130)),
    ]

    inicio_barras_x = retrato_rect.right + 145
    espacio_disponible = panel_rect.right - inicio_barras_x - 20
    ancho_bloque = max(120, espacio_disponible // len(stats) - 14)
    alto_barra = 14

    for idx, (etiqueta, valor, maximo, color_barra) in enumerate(stats):
        bx = inicio_barras_x + idx * (ancho_bloque + 14)
        by_texto = panel_rect.y + 14
        by_barra = panel_rect.y + 38

        lbl = fuente_stat.render(f"{etiqueta}: {valor}", True, (235, 240, 255))
        superficie.blit(lbl, (bx, by_texto))

        fondo_barra = pygame.Rect(bx, by_barra, ancho_bloque, alto_barra)
        pygame.draw.rect(superficie, (35, 40, 60), fondo_barra)

        ratio = 0.0 if maximo <= 0 else max(0.0, min(1.0, valor / maximo))
        ancho_relleno = int(ancho_bloque * ratio)
        if ancho_relleno > 0:
            pygame.draw.rect(superficie, color_barra, pygame.Rect(bx, by_barra, ancho_relleno, alto_barra))

        pygame.draw.rect(superficie, (200, 205, 230), fondo_barra, 2)

def dibujar_anuncio_game_over(superficie, motivo, nombre_jugador, ahora):
    if not motivo:
        return

    if motivo == "GUARDIANES":
        titulo = f"GAME OVER {nombre_jugador.upper()}"
        subtitulo = "ATAQUE DE GUARDIANES"
        color_borde = (255, 55, 85)
    elif motivo == "TIEMPO":
        titulo = "GAME OVER"
        subtitulo = "TIEMPO AGOTADO"
        color_borde = (255, 195, 0)
    else:
        return

    pulso = int(math.sin(ahora * 10) * 5)

    surf_titulo = fuente_evento_gigante.render(titulo, True, (255, 255, 255))
    surf_titulo_sombra = fuente_evento_gigante.render(titulo, True, (15, 15, 20))

    fuente_sub = pygame.font.SysFont(["Courier New", "Consolas", "Impact", "Arial Black"], 36, bold=True)
    surf_sub = fuente_sub.render(subtitulo, True, color_borde)
    surf_sub_sombra = fuente_sub.render(subtitulo, True, (15, 15, 20))

    pad_x, pad_y = 44, 28
    ancho_caja = max(surf_titulo.get_width(), surf_sub.get_width()) + pad_x * 2
    alto_caja = surf_titulo.get_height() + surf_sub.get_height() + 18 + pad_y * 2

    caja_rect = pygame.Rect(
        (ANCHO_PANTALLA - ancho_caja) // 2,
        (ALTO_PANTALLA - alto_caja) // 2 + pulso,
        ancho_caja,
        alto_caja,
    )

    velo = pygame.Surface((ANCHO_PANTALLA, ALTO_PANTALLA), pygame.SRCALPHA)
    velo.fill((0, 0, 0, 125))
    superficie.blit(velo, (0, 0))

    pygame.draw.rect(superficie, (16, 18, 28), caja_rect, border_radius=10)
    pygame.draw.rect(superficie, color_borde, caja_rect, 6, border_radius=10)

    x_titulo = caja_rect.centerx - surf_titulo.get_width() // 2
    y_titulo = caja_rect.y + pad_y

    x_sub = caja_rect.centerx - surf_sub.get_width() // 2
    y_sub = y_titulo + surf_titulo.get_height() + 16

    superficie.blit(surf_titulo_sombra, (x_titulo + 4, y_titulo + 4))
    superficie.blit(surf_titulo, (x_titulo, y_titulo))

    superficie.blit(surf_sub_sombra, (x_sub + 3, y_sub + 3))
    superficie.blit(surf_sub, (x_sub, y_sub))
#Comando de pygame para setear un timer 
reloj = pygame.time.Clock()


#####A PARTIR DE ESTE MOMENTO ES LO DE LA CEREMONIA DE VICTORIA####

estado_juego = "JUGANDO"

rivales_ejemplo = [
    {"id_jugador": 2, "nombre": "NARANJA", "x": 4, "y": 3, "puntos": 20, "extrayendo": False},
    {"id_jugador": 3, "nombre": "VERDE", "x": 6, "y": 5, "puntos": 15, "extrayendo": False},
]

resultados_ejemplo = [
    {"id_jugador": 1, "nombre": "AZUL", "puntos": 1250, "energia": 800, "celdas": 5, "guardias": 2},
    {"id_jugador": 2, "nombre": "NARANJA", "puntos": 980, "energia": 600, "celdas": 3, "guardias": 1},
    {"id_jugador": 3, "nombre": "VERDE", "puntos": 750, "energia": 450, "celdas": 2, "guardias": 0},
]
ganador_partida = "Azul"

reloj = pygame.time.Clock()

vida_jugador = 100
vida_maxima = 100
ultimo_golpe_guardian = 0.0
cooldown_golpe = 1.5   #Cooldown entre golpes


#Esto se hace para visualizar los stats del jugador dentro de la partida
ataques_sufridos = 0
max_ataques_barra = 5    
energia_extraida = 0
max_energia_barra = 100    
celdas_obtenidas = 0
max_celdas_barra = 5

seleccionar_escenario("laboratorio_subterraneo")

fuente_evento_gigante = pygame.font.SysFont(
    ["Courier New", "Consolas", "Impact", "Arial Black"],
    54,
    bold=True
)


motivo_game_over = None
tiempo_inicio_game_over = 0.0
duracion_game_over = 8.0 #Lo meti a 8 segundos porque se me quedaba un monton de tiempo en la pantalla de victoria 

AUDIO_HABILITADO = False
sonido_victoria_reproducido = False
musica_victoria_ruta = os.path.join(CARPETA_ASSETS, "TheFinalCountdown.mp3")

try:
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    AUDIO_HABILITADO = True
except Exception as e:
    print("Aviso de audio:", e)
    AUDIO_HABILITADO = False


######3Seccion de pantalla de eleccion de escenarios#####
ESCENARIOS_MENU = [
    {
        "clave": "planta_industrial",
        "titulo": "PLANTA INDUSTRIAL",
        "dificultad": "FÁCIL",
        "color": (80, 220, 140),
        "desc": "Pulso del reactor y rutas directas.",
    },
    {
        "clave": "laboratorio_subterraneo",
        "titulo": "LABORATORIO SUBTERRÁNEO",
        "dificultad": "MEDIO",
        "color": (0, 205, 255),
        "desc": "Transferencia de celdas y pasillos técnicos.",
    },
    {
        "clave": "complejo_militar",
        "titulo": "COMPLEJO MILITAR",
        "dificultad": "DIFÍCIL",
        "color": (255, 75, 95),
        "desc": "4 guardianes y -50% de energía a mitad de partida.",
    },
]


def dibujar_menu_escenarios(superficie, seleccionado_idx, ahora):
    superficie.fill((14, 18, 28))

    fuente_titulo = pygame.font.SysFont(["Courier New", "Consolas", "Arial Black"], 44, bold=True)
    fuente_sub = pygame.font.SysFont("Arial", 20, bold=True)
    fuente_card_titulo = pygame.font.SysFont(["Courier New", "Consolas", "Arial Black"], 22, bold=True)
    fuente_desc = pygame.font.SysFont("Arial", 16)

    txt_titulo = fuente_titulo.render("SELECCIONA EL ESCENARIO", True, (255, 255, 255))
    superficie.blit(txt_titulo, (ANCHO_PANTALLA // 2 - txt_titulo.get_width() // 2, 65))

    txt_ayuda = fuente_sub.render(
        "Haz clic en un mapa o presiona [1] [2] [3]  •  [ENTER] para iniciar  •  [ESC] salir",
        True,
        (170, 185, 210),
    )
    superficie.blit(txt_ayuda, (ANCHO_PANTALLA // 2 - txt_ayuda.get_width() // 2, 122))

    cantidad = len(ESCENARIOS_MENU)
    margen_lateral = 60
    espacio = 28
    ancho_tarjeta = (ANCHO_PANTALLA - 2 * margen_lateral - espacio * (cantidad - 1)) // cantidad
    alto_tarjeta = 280
    y_tarjeta = (ALTO_PANTALLA - alto_tarjeta) // 2 + 15

    pos_mouse = pygame.mouse.get_pos()
    rects_tarjetas = []

    for idx, item in enumerate(ESCENARIOS_MENU):
        x_tarjeta = margen_lateral + idx * (ancho_tarjeta + espacio)
        rect = pygame.Rect(x_tarjeta, y_tarjeta, ancho_tarjeta, alto_tarjeta)
        hover = rect.collidepoint(pos_mouse)
        activa = (idx == seleccionado_idx) or hover

        pulso_y = int(math.sin(ahora * 6 + idx) * 3) if activa else 0
        rect_dibujo = rect.move(0, pulso_y)

        color_fondo = (28, 36, 54) if activa else (20, 25, 38)
        grosor_borde = 4 if activa else 2

        pygame.draw.rect(superficie, color_fondo, rect_dibujo, border_radius=12)
        pygame.draw.rect(superficie, item["color"], rect_dibujo, grosor_borde, border_radius=12)

        #Marca de dificultad
        badge_rect = pygame.Rect(rect_dibujo.x + 18, rect_dibujo.y + 18, 125, 30)
        pygame.draw.rect(superficie, item["color"], badge_rect, border_radius=6)
        lbl_dif = fuente_sub.render(item["dificultad"], True, (12, 15, 22))
        superficie.blit(lbl_dif, (badge_rect.centerx - lbl_dif.get_width() // 2, badge_rect.centery - lbl_dif.get_height() // 2))

        #acceso rapido
        lbl_num = fuente_sub.render(f"[{idx + 1}]", True, (220, 225, 240))
        superficie.blit(lbl_num, (rect_dibujo.right - 48, rect_dibujo.y + 22))

        #nombre del maapa
        lbl_nombre = fuente_card_titulo.render(item["titulo"], True, (255, 255, 255))
        superficie.blit(lbl_nombre, (rect_dibujo.x + 18, rect_dibujo.y + 75))

        #descripcion del mapa
        lbl_desc = fuente_desc.render(item["desc"], True, (205, 215, 230))
        superficie.blit(lbl_desc, (rect_dibujo.x + 18, rect_dibujo.y + 125))

        
        btn_rect = pygame.Rect(rect_dibujo.x + 18, rect_dibujo.bottom - 56, ancho_tarjeta - 36, 38)
        pygame.draw.rect(
            superficie,
            item["color"] if activa else (42, 50, 70),
            btn_rect,
            border_radius=8,
        )
        txt_btn = fuente_sub.render("JUGAR", True, (12, 15, 22) if activa else (235, 240, 255))
        superficie.blit(txt_btn, (btn_rect.centerx - txt_btn.get_width() // 2, btn_rect.centery - txt_btn.get_height() // 2))

        rects_tarjetas.append((rect, idx, item["clave"]))

    return rects_tarjetas



DURACION_CUENTA_REGRESIVA = 5.0
DURACION_ANUNCIO_ENGAGE = 1.1

tiempo_inicio_cuenta = 0.0
tiempo_fin_engage = 0.0
briefing_mision = "Se leal a tu nación y lucha contra las fuerzas robóticas, roba la energía de su reactor"


def envolver_texto_retro(texto, fuente, ancho_maximo):
    palabras = texto.split()
    lineas = []
    actual = ""
    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        if fuente.size(prueba)[0] <= ancho_maximo:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def dibujar_cuenta_regresiva_retro(superficie, restante, ahora):
    superficie.fill((10, 13, 22))

    #Lineas tipo retro
    for y_scan in range(0, ALTO_PANTALLA, 6):
        pygame.draw.line(superficie, (18, 24, 38), (0, y_scan), (ANCHO_PANTALLA, y_scan), 1)

    fuente_tag = pygame.font.SysFont(["Courier New", "Consolas", "Arial Black"], 22, bold=True)
    fuente_briefing = pygame.font.SysFont(["Courier New", "Consolas", "Arial Black"], 26, bold=True)
    fuente_numero = pygame.font.SysFont(["Courier New", "Consolas", "Impact", "Arial Black"], 130, bold=True)
    fuente_pie = pygame.font.SysFont(["Courier New", "Consolas", "Arial"], 18, bold=True)

    #Marco principal
    marco = pygame.Rect(48, 42, ANCHO_PANTALLA - 96, ALTO_PANTALLA - 84)
    pygame.draw.rect(superficie, (16, 22, 36), marco, border_radius=12)
    pygame.draw.rect(superficie, (0, 225, 255), marco, 4, border_radius=12)

    lbl_tag = fuente_tag.render("DIRECTIVA DE MISIÓN", True, (255, 215, 0))
    superficie.blit(lbl_tag, (ANCHO_PANTALLA // 2 - lbl_tag.get_width() // 2, marco.y + 26))

    
    lineas = envolver_texto_retro(briefing_mision, fuente_briefing, marco.width - 90)
    y_linea = marco.y + 70
    for linea in lineas:
        surf_l = fuente_briefing.render(linea, True, (240, 248, 255))
        superficie.blit(surf_l, (ANCHO_PANTALLA // 2 - surf_l.get_width() // 2, y_linea))
        y_linea += surf_l.get_height() + 8

    #Cuenta regresiva
    numero_actual = max(1, min(5, int(math.ceil(restante))))
    pulso_escala = 1.0 + 0.08 * abs(math.sin(ahora * math.pi * 2))
    surf_num_base = fuente_numero.render(str(numero_actual), True, (255, 75, 110))
    surf_num_sombra_base = fuente_numero.render(str(numero_actual), True, (25, 12, 24))

    nuevo_w = int(surf_num_base.get_width() * pulso_escala)
    nuevo_h = int(surf_num_base.get_height() * pulso_escala)
    surf_num = pygame.transform.smoothscale(surf_num_base, (nuevo_w, nuevo_h))
    surf_num_sombra = pygame.transform.smoothscale(surf_num_sombra_base, (nuevo_w, nuevo_h))

    x_num = ANCHO_PANTALLA // 2 - surf_num.get_width() // 2
    y_num = marco.centery - 15

    superficie.blit(surf_num_sombra, (x_num + 6, y_num + 6))
    superficie.blit(surf_num, (x_num, y_num))

    lbl_pie = fuente_pie.render("PREPARANDO SISTEMAS...  [ENTER] SALTAR CONTEO", True, (150, 175, 205))
    superficie.blit(lbl_pie, (ANCHO_PANTALLA // 2 - lbl_pie.get_width() // 2, marco.bottom - 44))


def dibujar_anuncio_engage(superficie, ahora):
    if ahora >= tiempo_fin_engage:
        return

    restante_eng = max(0.0, tiempo_fin_engage - ahora)
    #Golpe inicial grande 
    escala = 1.0 + (0.25 * (restante_eng / DURACION_ANUNCIO_ENGAGE))

    fuente_eng = pygame.font.SysFont(["Courier New", "Consolas", "Impact", "Arial Black"], 112, bold=True)
    surf_sombra_raw = fuente_eng.render("ENGAGE", True, (15, 15, 22))
    surf_borde_raw = fuente_eng.render("ENGAGE", True, (255, 65, 85))
    surf_texto_raw = fuente_eng.render("ENGAGE", True, (255, 220, 45))

    w = int(surf_texto_raw.get_width() * escala)
    h = int(surf_texto_raw.get_height() * escala)

    surf_sombra = pygame.transform.smoothscale(surf_sombra_raw, (w, h))
    surf_borde = pygame.transform.smoothscale(surf_borde_raw, (w, h))
    surf_texto = pygame.transform.smoothscale(surf_texto_raw, (w, h))

    cx = ANCHO_PANTALLA // 2 - w // 2
    cy = ALTO_PANTALLA // 2 - h // 2

    # Sombra y contorno grueso tipo Cuphead yayyaa
    superficie.blit(surf_sombra, (cx + 8, cy + 8))
    for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4)):
        superficie.blit(surf_borde, (cx + dx, cy + dy))
    superficie.blit(surf_texto, (cx, cy))

def activar_partida_con_engage(ahora):
    global estado_juego, tiempo_fin_engage, partida
    estado_juego = "JUGANDO"
    tiempo_fin_engage = ahora + DURACION_ANUNCIO_ENGAGE
    #Reinicia reloj de la partida
    if hasattr(partida, "inicio"):
        partida.inicio = ahora



def iniciar_modo_jugando(escenario=None):
    global estado_juego, sonido_victoria_reproducido, tiempo_inicio_cuenta, tiempo_fin_engage
    if escenario:
        seleccionar_escenario(escenario)
    estado_juego = "CUENTA_REGRESIVA"
    tiempo_inicio_cuenta = time.monotonic()
    tiempo_fin_engage = 0.0
    sonido_victoria_reproducido = False
    if AUDIO_HABILITADO:
        pygame.mixer.music.stop()


estado_juego = "MENU_ESCENARIO"
escenario_seleccionado_idx = 0
rects_menu_escenarios = []


VENTANA_COMANDO_MOV = 0.07
VENTANA_ACCION_SERIAL = 0.20

ultimo_comando_mov = ""
tiempo_ultimo_mov = 0.0
tiempo_ultima_accion = 0.0



while True:
    #Esto me permite procesar los elementos una vez 
    for evento in pygame.event.get():

        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if estado_juego == "MENU_ESCENARIO":
                for rect_t, idx_t, clave_t in rects_menu_escenarios:
                    if rect_t.collidepoint(evento.pos):
                        escenario_seleccionado_idx = idx_t
                        iniciar_modo_jugando(clave_t)
                        break


        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()



            elif estado_juego == "MENU_ESCENARIO":
                if evento.key in (pygame.K_LEFT, pygame.K_a):
                    escenario_seleccionado_idx = (escenario_seleccionado_idx - 1) % len(ESCENARIOS_MENU)
                elif evento.key in (pygame.K_RIGHT, pygame.K_d):
                    escenario_seleccionado_idx = (escenario_seleccionado_idx + 1) % len(ESCENARIOS_MENU)
                elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    iniciar_modo_jugando(ESCENARIOS_MENU[escenario_seleccionado_idx]["clave"])
                elif evento.key == pygame.K_1:
                    iniciar_modo_jugando("planta_industrial")
                elif evento.key == pygame.K_2:
                    iniciar_modo_jugando("laboratorio_subterraneo")
                elif evento.key == pygame.K_3:
                    iniciar_modo_jugando("complejo_militar")
            
            elif estado_juego == "CUENTA_REGRESIVA":
                if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    activar_partida_con_engage(time.monotonic())

            else:
                if evento.key == pygame.K_1:
                    iniciar_modo_jugando("planta_industrial")
                elif evento.key == pygame.K_2:
                    iniciar_modo_jugando("laboratorio_subterraneo")
                elif evento.key == pygame.K_3:
                    iniciar_modo_jugando("complejo_militar")
                elif evento.key == pygame.K_m:
                    estado_juego = "MENU_ESCENARIO"
                    sonido_victoria_reproducido = False
                    if AUDIO_HABILITADO:
                        pygame.mixer.music.stop()
                elif evento.key == pygame.K_v:
                    if estado_juego == "JUGANDO":
                        sonido_victoria_reproducido = False
                        estado_juego = "VICTORIA"
                    else:
                        iniciar_modo_jugando()
            

    #OJO, Segun el estado es Jugando o Victoria alterno la pantalla
    if estado_juego == "MENU_ESCENARIO":
        rects_menu_escenarios = dibujar_menu_escenarios(
            ventana,
            escenario_seleccionado_idx,
            time.monotonic(),
        )

    elif estado_juego == "CUENTA_REGRESIVA":
      ahora = time.monotonic()
      restante = DURACION_CUENTA_REGRESIVA - (ahora - tiempo_inicio_cuenta)
      if restante <= 0:
          activar_partida_con_engage(ahora)
      else:
          dibujar_cuenta_regresiva_retro(ventana, restante, ahora)


    elif estado_juego == "JUGANDO":
        ahora = time.monotonic()

        ventana.fill((20, 25, 35))

        teclas = pygame.key.get_pressed()

        ########COMANDOS DEL ARDUINO EN ESTE MOMENTO#########
        if puerto_serial and puerto_serial.in_waiting > 0:
            try:
                while puerto_serial.in_waiting > 0:
                    linea = puerto_serial.readline().decode("utf-8", errors="ignore").strip()
                    if linea:
                        print("SERIAL:", repr(linea))
                    if linea in ("ARRIBA", "ABAJO", "IZQUIERDA", "DERECHA"):
                        ultimo_comando_mov = linea
                        tiempo_ultimo_mov = ahora
                    elif linea == "ACCION":
                        tiempo_ultima_accion = ahora
            except Exception:
                pass

        comando_hardware = (
            ultimo_comando_mov
            if (ultimo_comando_mov and (ahora - tiempo_ultimo_mov) <= VENTANA_COMANDO_MOV)
            else ""
        )
        accion_hardware = (ahora - tiempo_ultima_accion) <= VENTANA_ACCION_SERIAL
        dibujar_mapa(ventana, matriz_activa)
 #Logica normal
        #Detectar si el jugador está en una trampa
        en_trampa = any(
            obs.tipo == "trampa"
            and jugador.rect.colliderect(obs.rect)
            for obs in obstaculos
        )

        if en_trampa:
            jugador.velocidad_actual = 2
        else:
            jugador.velocidad_actual = jugador.velocidad_base

        #Actualizar al jugador
        jugador.Mover(teclas, comando_hardware, obstaculos)

        #Actualizar y dibujar guardianes
        for guardian in guardianes:
            guardian.actualizar(jugador)
            guardian.dibujar(ventana)

            if jugador.rect.colliderect(guardian.rect) and (ahora - ultimo_golpe_guardian) >= cooldown_golpe:
                vida_jugador = max(0, vida_jugador - 20)
                ataques_sufridos += 1
                jugador_logico.puntos = max(0, jugador_logico.puntos - 10)
                ultimo_golpe_guardian = ahora
                jugador_logico.extrayendo = False
                print(f"¡Golpe! Vida: {vida_jugador} | Puntos: {jugador_logico.puntos}")

                if ataques_sufridos >= 5 or vida_jugador <= 0:
                    if motivo_game_over is None:
                        motivo_game_over = "GUARDIANES"
                        tiempo_inicio_game_over = ahora
                        jugador_logico.extrayendo = False
                    
        #Dibujar obstáculos
        for obs in obstaculos:
            obs.dibujar(ventana)

        #Dibujar jugador al final para que quede visible
        jugador.dibujar(ventana)

        
        adaptador.sincronizar_jugador(jugador, jugador_logico) #Sincronizco las celdas y activo las terminales de energia

        for celda_item in celdas_energia[:]:
            if jugador.rect.colliderect(celda_item):
                celdas_energia.remove(celda_item)
                celdas_obtenidas += 1
                jugador_logico.sumar_puntos(10)

        for term in partida.terminales:
            estaba_activa = term.activada
            term.activar(jugador_logico)
            if not estaba_activa and term.activada:
                celdas_obtenidas += 1

#####Logica para recargar y extraer energia dentro del reactor manteniedo E
        partida.reactor.recargar_si_corresponde(ahora)
        extrayendo_input = teclas[pygame.K_e] or accion_hardware

        if accion_hardware:
            print(
                "ACCION recibida | cerca:",
                partida.reactor.jugador_cerca(jugador_logico),
                "| energia_reactor:",
                partida.reactor.energia_actual,
            )

        if extrayendo_input and partida.reactor.jugador_cerca(jugador_logico) and partida.reactor.energia_actual > 0:
            jugador_logico.extrayendo = True
            if ahora - jugador_logico.ultimo_ciclo_extraccion >= partida.reactor.intervalo:
                extraido = partida.reactor.extraer(jugador_logico, ahora)
                energia_extraida += extraido
                jugador_logico.ultimo_ciclo_extraccion = ahora
        else:
            jugador_logico.extrayendo = False

        fuente_hud = pygame.font.SysFont("Arial", 18, bold=True)
        for term in partida.terminales:
            tx, ty = adaptador.celda_a_pixeles(term.x, term.y)
            rect_term = pygame.Rect(tx, ty, TAMANO_CELDA, TAMANO_CELDA)
            if USAR_IMAGEN_TERMINAL:
                superficie_img_term = (
                    img_celda_lab
                    if (escenario_actual == "laboratorio_subterraneo" and USAR_IMAGENES_LAB)
                    else img_terminal
                )
                ventana.blit(superficie_img_term, rect_term)
                color_estado = (0, 255, 120) if term.activada else (255, 215, 0)
                pygame.draw.rect(ventana, color_estado, rect_term, 2)
            else:
                color_term = (0, 255, 120) if term.activada else (255, 215, 0)
                pygame.draw.rect(ventana, color_term, rect_term, 3)

        texto_hud = fuente_hud.render(
            f"Vida: {vida_jugador}/{vida_maxima} | Tiempo: {int(partida.tiempo_restante(ahora))}s | Puntos: {jugador_logico.puntos}/{partida.meta} | Reactor: {partida.reactor.energia_actual}/{partida.reactor.energia_maxima}",
            True,
            BLANCO,
        )
        ventana.blit(texto_hud, (20, 15))

        if evento_escenario:
            if isinstance(evento_escenario, EventoTransferenciaCeldasLab):
                evento_escenario.actualizar(
                    partida,
                    jugador_logico,
                    ahora,
                    celdas_jugador=celdas_obtenidas,
                    rivales=rivales_ejemplo,
                )
                if evento_escenario.celdas_transferidas > 0:
                    celdas_obtenidas = 0
            else:
                antes_activado = getattr(evento_escenario, "activado", False)
                evento_escenario.actualizar(partida, jugador_logico, ahora)
                if isinstance(evento_escenario, EventoReduccionEnergiaMilitar) and not antes_activado and evento_escenario.activado:
                    energia_extraida = energia_extraida // 2

            anuncio_texto, anuncio_color = evento_escenario.obtener_anuncio(ahora)

            if anuncio_texto:
                pulso = int(math.sin(ahora * 14) * 6)
                superficie_texto = fuente_evento_gigante.render(anuncio_texto, True, (255, 255, 255))
                superficie_sombra = fuente_evento_gigante.render(anuncio_texto, True, (15, 15, 20))

                pad_x, pad_y = 36, 22
                ancho_caja = superficie_texto.get_width() + pad_x * 2
                alto_caja = superficie_texto.get_height() + pad_y * 2

                caja_rect = pygame.Rect(
                    (ANCHO_PANTALLA - ancho_caja) // 2,
                    (ALTO_PANTALLA - alto_caja) // 2 + pulso,
                    ancho_caja,
                    alto_caja
                )

                pygame.draw.rect(ventana, (18, 22, 32), caja_rect, border_radius=8)
                pygame.draw.rect(ventana, anuncio_color, caja_rect, 6, border_radius=8)

                pos_texto_x = caja_rect.x + pad_x
                pos_texto_y = caja_rect.y + pad_y

                ventana.blit(superficie_sombra, (pos_texto_x + 4, pos_texto_y + 4))
                ventana.blit(superficie_texto, (pos_texto_x, pos_texto_y))

        # Fin automatico de la partida por tiempo 
        if partida.finalizar_si_corresponde(ahora):
            if motivo_game_over is None:
                motivo_game_over = "TIEMPO"
                tiempo_inicio_game_over = ahora
                jugador_logico.extrayendo = False


        
        rivales_px = adaptador.adaptar_jugadores_arena(rivales_ejemplo)
        for rival in rivales_px:
            rect_rival = pygame.Rect(rival["px"], rival["py"], TAMANO_CELDA, TAMANO_CELDA)
            nombre_rival = str(rival.get("nombre", "")).strip().upper()

            if USAR_IMAGENES_RIVALES:
                if "VERDE" in nombre_rival:
                    ventana.blit(img_rival_verde, rect_rival)
                else:
                    ventana.blit(img_rival_naranja, rect_rival)
            else:
                pygame.draw.rect(ventana, (255, 140, 0), rect_rival)
                pygame.draw.rect(ventana, (255, 255, 255), rect_rival, 2)


        dibujar_barra_inferior_deltarune(
            ventana,
            jugador_logico.nombre,
            ataques_sufridos,
            max_ataques_barra,
            energia_extraida,
            max_energia_barra,
            celdas_obtenidas,
            max_celdas_barra,
        )

        if motivo_game_over is not None:
            transcurrido_go = ahora - tiempo_inicio_game_over
            if transcurrido_go < duracion_game_over:
                dibujar_anuncio_game_over(ventana, motivo_game_over, jugador_logico.nombre, ahora)
            else:
                if not partida.resultados_finales:
                    partida.resultados_finales = [
                        {
                            "id_jugador": j.id_jugador,
                            "nombre": j.nombre,
                            "puntos": j.puntos,
                        }
                        for j in sorted(
                            partida.jugadores,
                            key=lambda j: (-j.puntos, j.id_jugador),
                        )
                    ]
                motivo_game_over = None
                sonido_victoria_reproducido = False
                estado_juego = "VICTORIA"

        dibujar_anuncio_engage(ventana, ahora)        



    elif estado_juego == "VICTORIA":

        rects_menu_escenarios = []
        if estado_juego == "MENU_ESCENARIO":
            rects_menu_escenarios = dibujar_menu_escenarios(
                ventana,
                escenario_seleccionado_idx,
                time.monotonic(),
    )
        resultados_base = partida.resultados_finales or [
            {
                "id_jugador": j.id_jugador,
                "nombre": j.nombre,
                "puntos": j.puntos,
            }
            for j in sorted(partida.jugadores, key=lambda j: (-j.puntos, j.id_jugador))
        ]

        resultados_enriquecidos = []
        for r in resultados_base:
            copia = dict(r)
            if copia.get("nombre", "").strip().upper() == str(jugador_logico.nombre).strip().upper():
                copia["energia"] = energia_extraida
                copia["celdas"] = celdas_obtenidas
                copia["golpes_sufridos"] = ataques_sufridos
                copia["guardias"] = ataques_sufridos
                copia["vida"] = vida_jugador
            resultados_enriquecidos.append(copia)

        ganador_adaptado, stats_adaptados = adaptador.adaptar_resultados_victoria(
            resultados_enriquecidos
        )
        ceremonia_victoria(ventana, ganador_adaptado, stats_adaptados, ahora)

        if not sonido_victoria_reproducido:
            sonido_victoria_reproducido = True
            if AUDIO_HABILITADO and os.path.exists(musica_victoria_ruta):
                try:
                    pygame.mixer.music.load(musica_victoria_ruta)
                    pygame.mixer.music.set_volume(0.4)
                    pygame.mixer.music.play(loops=-1, start=13.0)
                except Exception as e:
                    print("No se pudo reproducir la musica de victoria:", e)

    # Aqui actualizo la pantalla
    pygame.display.flip()
    reloj.tick(60)


     

