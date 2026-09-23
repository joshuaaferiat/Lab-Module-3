// Phys 39 Module 3 - Part 2
// Fixed-direction manual TEC control
// A0: thermistor
// A1: trim pot -> PWM command
// Pin 9: fixed LOW
// Pin 10: PWM to H-bridge

const int THERMISTOR_PIN = A0;
const int POT_PIN = A1;
const int HBRIDGE_PIN_1 = 9;
const int HBRIDGE_PIN_2 = 10;

const int ADC_SAMPLES = 200;              // 100 to 1000 allowed
const unsigned long PRINT_INTERVAL_MS = 200;

// Thermistor constants -- Module 2 values, confirmed in
// docs/module_notes/module_02_instrument_pieces.md §1:
//   SERIES_RESISTOR / NOMINAL_RESISTANCE: 100 kOhm nominal/rated value (not an
//     independent multimeter measurement -- same caveat as the Module 2 note).
//   BETA_COEFFICIENT: 4540 K, datasheet B57861S0104F040V24, confirmed by the
//     team directly from the datasheet.
const float SERIES_RESISTOR = 100000.0;
const float NOMINAL_RESISTANCE = 100000.0;
const float NOMINAL_TEMPERATURE_C = 25.0;
const float BETA_COEFFICIENT = 4540.0;
const float ADC_MAX = 1023.0;

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

  // Safety: PWM starts at zero.
digitalWrite(HBRIDGE_PIN_1, LOW);
digitalWrite(HBRIDGE_PIN_2, LOW);
analogWrite(HBRIDGE_PIN_2, 0);

Serial.begin(9600);

  startTime = millis();
  lastPrint = 0;

Serial.println("Part 2 fixed-direction manual TEC control");
Serial.println("Turn trim pot to zero before applying TEC power.");
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

digitalWrite(HBRIDGE_PIN_1, LOW);
analogWrite(HBRIDGE_PIN_2, pwm);

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

Serial.print(", Active PWM pin: ");
Serial.println(HBRIDGE_PIN_2);
}
}