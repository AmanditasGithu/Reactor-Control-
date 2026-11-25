// Definición de pines para el panel físico del Reactor
const int PIN_ARRIBA    = 22;
const int PIN_ABAJO     = 24;
const int PIN_IZQUIERDA = 26;
const int PIN_DERECHA   = 28;
const int PIN_ACCION    = 30;

const unsigned long INTERVALO_ENVIO_MS = 25;
unsigned long ultimoEnvioMs = 0;

void setup() {
  // Inicializar comunicación Serial
  Serial.begin(115200);
  while (!Serial); // Esperar conexión serial

  // Configurar todos los pines como entradas con resistencia Pull-Up interna
  pinMode(PIN_ARRIBA, INPUT_PULLUP);
  pinMode(PIN_ABAJO, INPUT_PULLUP);
  pinMode(PIN_IZQUIERDA, INPUT_PULLUP);
  pinMode(PIN_DERECHA, INPUT_PULLUP);
  pinMode(PIN_ACCION, INPUT_PULLUP);

  Serial.println("=== SISTEMA LISTO: PROBANDO 5 BOTONES ===");
}

void loop() {
  unsigned long ahoraMs = millis();
  if (ahoraMs - ultimoEnvioMs < INTERVALO_ENVIO_MS) {
    return;
  }

  bool envioAlgo = false;

  // Leer y verificar cada botón individualmente (LOW = presionado)
  if (digitalRead(PIN_ARRIBA) == LOW) {
    Serial.println("ARRIBA");
    envioAlgo = true;
  }
  if (digitalRead(PIN_ABAJO) == LOW) {
    Serial.println("ABAJO");
    envioAlgo = true;
  }
  if (digitalRead(PIN_IZQUIERDA) == LOW) {
    Serial.println("IZQUIERDA");
    envioAlgo = true;
  }
  if (digitalRead(PIN_DERECHA) == LOW) {
    Serial.println("DERECHA");
    envioAlgo = true;
  }
  if (digitalRead(PIN_ACCION) == LOW) {
    Serial.println("ACCION");
    envioAlgo = true;
  }
  if (envioAlgo) {
    ultimoEnvioMs = ahoraMs;
  }
}
