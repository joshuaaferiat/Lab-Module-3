// Phys 39 Module 3 - Part 3
// Python-commanded TEC control
// A0: thermistor
// Pin 9 / Pin 10: H-bridge control signals
//
// Experimentally verified direction mapping:
//   HEAT -> pin 9 LOW, pin 10 PWM
//   COOL -> pin 9 PWM, pin 10 LOW

const int THERMISTOR_PIN = A0;
const int HBRIDGE_PIN_1 = 9;
const int HBRIDGE_PIN_2 = 10;

const int ADC_SAMPLES = 200;
const unsigned long PRINT_INTERVAL_MS = 200;

// Thermistor constants -- Module 2 values.
const float SERIES_RESISTOR = 100000.0;
const float NOMINAL_RESISTANCE = 100000.0;
const float NOMINAL_TEMPERATURE_C = 25.0;
const float BETA_COEFFICIENT = 4540.0;
const float ADC_MAX = 1023.0;

unsigned long startTime;
unsigned long lastPrint = 0;
int pwm = 0;
bool heating = false;

float readTemperatureC() {
  long sum = 0;

  for (int i = 0; i < ADC_SAMPLES; i++) {
    sum += analogRead(THERMISTOR_PIN);
    delayMicroseconds(200);
  }

  float adc = sum / (float)ADC_SAMPLES;

  if (adc <= 0 || adc >= ADC_MAX) {
    return NAN;
  }

  // Divider assumption:
  // 5V -> series resistor -> A0 -> thermistor -> GND
  float resistance = SERIES_RESISTOR * adc / (ADC_MAX - adc);

  // Beta equation
  float steinhart = resistance / NOMINAL_RESISTANCE;
  steinhart = log(steinhart);
  steinhart /= BETA_COEFFICIENT;
  steinhart += 1.0 / (NOMINAL_TEMPERATURE_C + 273.15);
  steinhart = 1.0 / steinhart;
  steinhart -= 273.15;

  return steinhart;
}

void applyOutput() {
  // Only one bridge input receives PWM; the other stays LOW.
  if (heating) {
    analogWrite(HBRIDGE_PIN_1, 0);
    analogWrite(HBRIDGE_PIN_2, pwm);
  } else {
    analogWrite(HBRIDGE_PIN_1, pwm);
    analogWrite(HBRIDGE_PIN_2, 0);
  }
}

bool parsePwm(String text, int &value) {
  if (text.length() == 0) {
    return false;
  }

  int index = 0;
  bool negative = false;
  char first = text.charAt(0);
  if (first == '-' || first == '+') {
    negative = first == '-';
    index++;
  }
  if (index == text.length()) {
    return false;
  }

  // Saturate while parsing so arbitrarily large numeric requests clamp safely.
  long magnitude = 0;
  for (; index < text.length(); index++) {
    char digit = text.charAt(index);
    if (digit < '0' || digit > '9') {
      return false;
    }
    if (magnitude < 256) {
      magnitude = magnitude * 10 + (digit - '0');
      if (magnitude > 256) {
        magnitude = 256;
      }
    }
  }

  value = negative ? 0 : (magnitude > 255 ? 255 : (int)magnitude);
  return true;
}

void parseCommand(String command) {
  command.trim();
  String tokens[5];
  int tokenCount = 0;
  int cursor = 0;

  // Accept exactly: SET PWM <integer> DIR HEAT|COOL. Invalid input is ignored,
  // leaving the last valid output unchanged.
  while (cursor < command.length()) {
    while (cursor < command.length() &&
           (command.charAt(cursor) == ' ' || command.charAt(cursor) == '\t')) {
      cursor++;
    }
    if (cursor >= command.length()) {
      break;
    }
    if (tokenCount >= 5) {
      return;
    }
    int end = cursor;
    while (end < command.length() && command.charAt(end) != ' ' &&
           command.charAt(end) != '\t') {
      end++;
    }
    tokens[tokenCount++] = command.substring(cursor, end);
    cursor = end;
  }

  if (tokenCount != 5 || !tokens[0].equalsIgnoreCase("SET") ||
      !tokens[1].equalsIgnoreCase("PWM") ||
      !tokens[3].equalsIgnoreCase("DIR")) {
    return;
  }

  int requestedPwm;
  if (!parsePwm(tokens[2], requestedPwm)) {
    return;
  }

  bool requestedHeating;
  if (tokens[4].equalsIgnoreCase("HEAT")) {
    requestedHeating = true;
  } else if (tokens[4].equalsIgnoreCase("COOL")) {
    requestedHeating = false;
  } else {
    return;
  }

  pwm = requestedPwm;
  heating = requestedHeating;
  applyOutput();
}

void setup() {
  pinMode(HBRIDGE_PIN_1, OUTPUT);
  pinMode(HBRIDGE_PIN_2, OUTPUT);

  // Safety: reset always disables both bridge inputs; only a valid serial
  // command can apply nonzero PWM afterward.
  analogWrite(HBRIDGE_PIN_1, 0);
  analogWrite(HBRIDGE_PIN_2, 0);

  Serial.begin(115200);
  Serial.println("Arduino ready. Use: SET PWM 120 DIR HEAT");

  startTime = millis();
  lastPrint = 0;
}

void loop() {
  if (Serial.available() > 0) {
    parseCommand(Serial.readStringUntil('\n'));
  }

  unsigned long now = millis();

  if (now - lastPrint >= PRINT_INTERVAL_MS) {
    lastPrint = now;

    float tempC = readTemperatureC();
    float elapsed = (now - startTime) / 1000.0;

    Serial.print("Temperature (C): ");
    if (isnan(tempC)) {
      Serial.print("nan");
    } else {
      Serial.print(tempC, 2);
    }

    Serial.print(", Time (s): ");
    Serial.print(elapsed, 2);

    Serial.print(", PWM: ");
    Serial.print(pwm);

    Serial.print(", Heat/Cool: ");
    Serial.println(heating ? 1 : 0);
  }
}
