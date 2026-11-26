// Definición de pines para el panel físico del Reactor
const int PIN_ARRIBA    = 22;
const int PIN_ABAJO     = 24;
const int PIN_IZQUIERDA = 26;
const int PIN_DERECHA   = 28;
const int PIN_ACCION    = 30;

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
  // Leer y verificar cada botón individualmente (LOW = presionado)
  if (digitalRead(PIN_ARRIBA) == LOW) {
    Serial.println("ARRIBA");
    delay(150);
  }
  if (digitalRead(PIN_ABAJO) == LOW) {
    Serial.println("ABAJO");
    delay(150);
  }
  if (digitalRead(PIN_IZQUIERDA) == LOW) {
    Serial.println("IZQUIERDA");
    delay(150);
  }
  if (digitalRead(PIN_DERECHA) == LOW) {
    Serial.println("DERECHA");
    delay(150);
  }
  if (digitalRead(PIN_ACCION) == LOW) {
    Serial.println("ACCION");
    delay(150);
  }
}