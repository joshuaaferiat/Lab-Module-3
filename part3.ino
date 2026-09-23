const int THERMISTOR_PIN = A0;
const int TRIM_POT_PIN = A1;
const int DIRECTION_PIN = 11;
const int H_BRIDGE_PIN_A = 9;
const int H_BRIDGE_PIN_B = 10;

const int ADC_SAMPLES = 100;
const float SERIES_RESISTOR_OHMS = 10000.0;
const float THERMISTOR_NOMINAL_OHMS = 10000.0;
const float THERMISTOR_NOMINAL_C = 25.0;
const float THERMISTOR_BETA = 3950.0;

// Set this based on the experimental result from Part 3.
// If the direction pin reads HIGH and the TEC heats, leave this as true.
// If HIGH produces cooling, set it to false.
const bool HEAT_ON_HIGH = true;

float readTemperatureC() {
  long adcTotal = 0;

  for (int sample = 0; sample < ADC_SAMPLES; sample++) {
    adcTotal += analogRead(THERMISTOR_PIN);
  }

  float adcAverage = adcTotal / (float)ADC_SAMPLES;
  if (adcAverage <= 0.0 || adcAverage >= 1023.0) {
    return NAN;
  }

  float thermistorResistance = SERIES_RESISTOR_OHMS * (1023.0 / adcAverage - 1.0);
  float nominalTemperatureK = THERMISTOR_NOMINAL_C + 273.15;
  float steinhart = log(thermistorResistance / THERMISTOR_NOMINAL_OHMS);
  steinhart /= THERMISTOR_BETA;
  steinhart += 1.0 / nominalTemperatureK;
  steinhart = 1.0 / steinhart;

  return steinhart - 273.15;
}

void applyPWMDirection(int pwmValue, bool heating) {
  if (heating) {
    analogWrite(H_BRIDGE_PIN_A, 0);
    analogWrite(H_BRIDGE_PIN_B, pwmValue);
  } else {
    analogWrite(H_BRIDGE_PIN_A, pwmValue);
    analogWrite(H_BRIDGE_PIN_B, 0);
  }
}

void setup() {
  pinMode(H_BRIDGE_PIN_A, OUTPUT);
  pinMode(H_BRIDGE_PIN_B, OUTPUT);
  pinMode(DIRECTION_PIN, INPUT);

  analogWrite(H_BRIDGE_PIN_A, 0);
  analogWrite(H_BRIDGE_PIN_B, 0);

  Serial.begin(115200);
}

void loop() {
  int trimPotAdc = analogRead(TRIM_POT_PIN);
  int pwmCommand = map(trimPotAdc, 0, 1023, 0, 255);

  bool directionHigh = (digitalRead(DIRECTION_PIN) == HIGH);
  bool heating = (HEAT_ON_HIGH && directionHigh) || (!HEAT_ON_HIGH && !directionHigh);

  float temperatureC = readTemperatureC();
  applyPWMDirection(pwmCommand, heating);

  Serial.print("Temperature (C): ");
  if (isnan(temperatureC)) {
    Serial.print("invalid");
  } else {
    Serial.print(temperatureC, 2);
  }
  Serial.print(", Time (s): ");
  Serial.print(millis() / 1000.0, 2);
  Serial.print(", PWM: ");
  Serial.print(pwmCommand);
  Serial.print(", Direction pin 11: ");
  Serial.print(directionHigh ? 1 : 0);
  Serial.print(", Heat/Cool: ");
  Serial.println(heating ? 1 : 0);

  delay(100);
}
