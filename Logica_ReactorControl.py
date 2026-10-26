import pygame
import sys
import math #para los guardianes 
import os #Para las imagenes 
import serial
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


            pygame.draw.rect(
                superficie,
                (65, 75, 90),
                celda_rect,
                1
            ) #Bordecillo ahi para la cuadricula 
    


cargar_Mapa(matriz_mapa)


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
            tooltip_rect = pygame.Rect(pos_mouse[0], pos_mouse[1] + 15, 200, 100)
            pygame.draw.rect(superficie, (10, 15, 25), tooltip_rect)
            pygame.draw.rect(superficie, (0, 220, 200), tooltip_rect, 2)

            fuente_tip = pygame.font.SysFont("Arial", 14)
            t1 = fuente_tip.render(f"Jugador: {jg['nombre']}", True, (255, 255, 255))
            t2 = fuente_tip.render(f"Energía Extraída: {jg.get('energia', 0)}", True, (200, 200, 200))
            t3 = fuente_tip.render(f"Celdas Recogidas: {jg.get('celdas', 0)}", True, (200, 200, 200))
            t4 = fuente_tip.render(f"Guardias Evitados: {jg.get('guardias', 0)}", True, (200, 200, 200))

            superficie.blit(t1, (tooltip_rect.x + 10, tooltip_rect.y + 10))
            superficie.blit(t2, (tooltip_rect.x + 10, tooltip_rect.y + 30))
            superficie.blit(t3, (tooltip_rect.x + 10, tooltip_rect.y + 50))
            superficie.blit(t4, (tooltip_rect.x + 10, tooltip_rect.y + 70))


#Comando de pygame para setear un timer 
reloj = pygame.time.Clock()


#####A PARTIR DE ESTE MOMENTO ES LO DE LA CEREMONIA DE VICTORIA####

estado_juego = "JUGANDO"

datos_jugadores_ejemplo = [
    {"nombre": "AZUL", "puntos": 1250, "energia": 800,
    "celdas": 5, "guardias": 2},
    {"nombre": "NARANJA", "puntos": 980, "energia": 600,
    "celdas": 3, "guardias": 1},
    {"nombre": "VERDE", "puntos": 750, "energia": 450,
    "celdas": 2, "guardias": 0}
]

ganador_partida = "Azul"

reloj = pygame.time.Clock()
    
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

        #Dibujar obstáculos
        for obs in obstaculos:
            obs.dibujar(ventana)

        #Dibujar jugador al final para que quede visible
        jugador.dibujar(ventana)

    elif estado_juego == "VICTORIA":

        ceremonia_victoria(
            ventana,
            ganador_partida,
            datos_jugadores_ejemplo
        )

    #Aqui actualizo la pantalla
    pygame.display.flip()
    reloj.tick(60)


     

