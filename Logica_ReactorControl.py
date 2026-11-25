import pygame
import sys
import math #para los guardianes 
import os #Para las imagenes 
import serial
import time 
from Adapter import AdaptadorEstadoBackend
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

adaptador = AdaptadorEstadoBackend(OFFSET_X, OFFSET_Y, TAMANO_CELDA)

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


            pygame.draw.rect(
                superficie,
                (65, 75, 90),
                celda_rect,
                1
            ) #Bordecillo ahi para la cuadricula 
    


cargar_Mapa(matriz_mapa)
partida, jugador_logico = adaptador.crear_partida_integrada(
    coords_reactor[0], coords_reactor[1], coords_terminales
)

if not pygame.font.get_init():
    pygame.font.init()
def ceremonia_victoria(superficie,ganador,datos_jugadores):
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


from Eventos_Especiales import FabricaEventosEscenario

escenario_actual = "planta_industrial"
evento_escenario = FabricaEventosEscenario.crear_evento(escenario_actual)


fuente_evento_gigante = pygame.font.SysFont(
    ["Courier New", "Consolas", "Impact", "Arial Black"],
    54,
    bold=True
)


motivo_game_over = None
tiempo_inicio_game_over = 0.0
duracion_game_over = 8.0 #Lo meti a 8 segundos porque se me quedaba un monton de tiempo en la pantalla de victoria 






while True:
    #Esto me permite procesar los elementos una vez 
    for evento in pygame.event.get():

        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if evento.type == pygame.KEYDOWN:

            if evento.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

            #V alterna entre el mapa y la ceremonia
            elif evento.key == pygame.K_v:
                if estado_juego == "JUGANDO":
                    estado_juego = "VICTORIA"
                else:
                    estado_juego = "JUGANDO"

    #OJO, Segun el estado es Jugando o Victoria alterno la pantalla
    if estado_juego == "JUGANDO":
        ahora = time.monotonic()

        ventana.fill((20, 25, 35))

        teclas = pygame.key.get_pressed()

        ########COMANDOS DEL ARDUINO EN ESTE MOMENTO#########
        comando_hardware = ""
        if puerto_serial and puerto_serial.in_waiting>0:
            try:
                while puerto_serial.in_waiting > 0: ##Aqui le tuve que meter esto para que leyera las lineas acumuladas de golpe y se moviera rapido
                    linea = puerto_serial.readline().decode('utf-8').strip()
                    if linea in ["ARRIBA", "ABAJO", "IZQUIERDA", "DERECHA", "ACCION"]:
                        comando_hardware = linea
            except:
                pass



        dibujar_mapa(ventana, matriz_mapa)
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
        for term in partida.terminales:
            estaba_activa = term.activada
            term.activar(jugador_logico)
            if not estaba_activa and term.activada:
                celdas_obtenidas += 1

#####Logica para recargar y extraer energia dentro del reactor manteniedo E
        partida.reactor.recargar_si_corresponde(ahora)
        if teclas[pygame.K_e] and partida.reactor.jugador_cerca(jugador_logico) and partida.reactor.energia_actual > 0:
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
            color_term = (0, 255, 120) if term.activada else (255, 215, 0)
            pygame.draw.rect(ventana, color_term, pygame.Rect(tx, ty, TAMANO_CELDA, TAMANO_CELDA), 3)

        texto_hud = fuente_hud.render(
            f"Vida: {vida_jugador}/{vida_maxima} | Tiempo: {int(partida.tiempo_restante(ahora))}s | Puntos: {jugador_logico.puntos}/{partida.meta} | Reactor: {partida.reactor.energia_actual}/{partida.reactor.energia_maxima}",
            True,
            BLANCO,
        )
        ventana.blit(texto_hud, (20, 15))

        if evento_escenario:
            evento_escenario.actualizar(partida, jugador_logico, ahora)
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
                estado_juego = "VICTORIA"

    elif estado_juego == "VICTORIA":
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
                copia["vida"] = vida_jugador
            resultados_enriquecidos.append(copia)

        ganador_adaptado, stats_adaptados = adaptador.adaptar_resultados_victoria(
            resultados_enriquecidos
        )
        ceremonia_victoria(ventana, ganador_adaptado, stats_adaptados)
        

    #Aqui actualizo la pantalla
    pygame.display.flip()
    reloj.tick(60)


     

