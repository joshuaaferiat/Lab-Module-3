// Phys 39 Module 3 - Part 3
// Hardware-direction manual TEC control
// A0: thermistor
// A1: trim pot -> PWM command
// Pin 11: SPDT direction switch (common to pin 11, outer to 5V/GND)
// Pin 9 / Pin 10: H-bridge control signals
//
// Direction mapping:
//   Pin 11 HIGH -> pin 9 PWM, pin 10 LOW
//   Pin 11 LOW  -> pin 9 LOW, pin 10 PWM

const int THERMISTOR_PIN = A0;
const int POT_PIN = A1;
const int HBRIDGE_PIN_1 = 9;
const int HBRIDGE_PIN_2 = 10;
const int DIR_PIN = 11;

const int ADC_SAMPLES = 200;
const unsigned long PRINT_INTERVAL_MS = 200;

// Thermistor constants -- Module 2 values.
const float SERIES_RESISTOR = 100000.0;
const float NOMINAL_RESISTANCE = 100000.0;
const float NOMINAL_TEMPERATURE_C = 25.0;
const float BETA_COEFFICIENT = 4540.0;
const float ADC_MAX = 1023.0;

// After the Part 3 experiment, set this to the pin-11 state that HEATS.
// If pin 11 HIGH heats, keep HEAT_STATE = HIGH.
// If pin 11 LOW heats, change to HEAT_STATE = LOW.
const int HEAT_STATE = HIGH;

unsigned long startTime;
unsigned long lastPrint = 0;
bool armed = false;

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

void setup() {
  pinMode(HBRIDGE_PIN_1, OUTPUT);
  pinMode(HBRIDGE_PIN_2, OUTPUT);
  pinMode(DIR_PIN, INPUT);

  // Safety: PWM starts at zero.
  digitalWrite(HBRIDGE_PIN_1, LOW);
  digitalWrite(HBRIDGE_PIN_2, LOW);
  analogWrite(HBRIDGE_PIN_1, 0);
  analogWrite(HBRIDGE_PIN_2, 0);

  Serial.begin(9600);

  startTime = millis();
  lastPrint = 0;

  Serial.println("Part 3 hardware-direction manual TEC control");
  Serial.println("Turn trim pot to zero before applying TEC power.");
  Serial.print("HEAT_STATE is set to: ");
  Serial.println(HEAT_STATE == HIGH ? "HIGH" : "LOW");
}

void loop() {
  int potValue = analogRead(POT_PIN);
  int pwm = map(potValue, 0, 1023, 0, 255);
  pwm = constrain(pwm, 0, 255);

  // Startup safety latch:
  // PWM must be zero once after reset before any nonzero PWM is allowed.
  if (!armed) {
    if (pwm <= 0) {
      armed = true;
    } else {
      pwm = 0;
    }
  }

  int dirState = digitalRead(DIR_PIN);

  // Direction mapping from the assignment table:
  // Pin 11 HIGH -> pin 9 PWM, pin 10 LOW
  // Pin 11 LOW  -> pin 9 LOW, pin 10 PWM
  int activePin;

  if (dirState == HIGH) {
    analogWrite(HBRIDGE_PIN_1, pwm);
    digitalWrite(HBRIDGE_PIN_2, LOW);
    activePin = HBRIDGE_PIN_1;
  } else {
    digitalWrite(HBRIDGE_PIN_1, LOW);
    analogWrite(HBRIDGE_PIN_2, pwm);
    activePin = HBRIDGE_PIN_2;
  }

  int heatCool = (dirState == HEAT_STATE) ? 1 : 0;

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

    Serial.print(", Direction input: ");
    Serial.print(dirState);

    Serial.print(", Active PWM pin: ");
    Serial.print(activePin);

    Serial.print(", Heat/Cool: ");
    Serial.println(heatCool);
  }
}