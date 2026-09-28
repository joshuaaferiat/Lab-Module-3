const int THERMISTOR_PIN = A0;
const int H_BRIDGE_PIN_A = 9;
const int H_BRIDGE_PIN_B = 10;

const int ADC_SAMPLES = 100;
const float SERIES_RESISTOR_OHMS = 10000.0;
const float THERMISTOR_NOMINAL_OHMS = 10000.0;
const float THERMISTOR_NOMINAL_C = 25.0;
const float THERMISTOR_BETA = 3950.0;

// Set this from the Part 3 hardware calibration.
// True means the heating output is on pin 10; false means it is on pin 9.
const bool HEATING_OUTPUT_IS_PIN_B = true;

int pwmCommand = 0;
bool heating = true;

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

void applyOutput() {
  int outputA = 0;
  int outputB = 0;

  if (heating) {
    outputA = 0;
    outputB = pwmCommand;
  } else {
    outputA = pwmCommand;
    outputB = 0;
  }

  // Use the experimentally verified mapping from Part 3.
  if (HEATING_OUTPUT_IS_PIN_B) {
    analogWrite(H_BRIDGE_PIN_A, (heating ? 0 : pwmCommand));
    analogWrite(H_BRIDGE_PIN_B, (heating ? pwmCommand : 0));
  } else {
    analogWrite(H_BRIDGE_PIN_A, (heating ? pwmCommand : 0));
    analogWrite(H_BRIDGE_PIN_B, (heating ? 0 : pwmCommand));
  }
}

void parseCommand(String command) {
  command.trim();
  if (command.length() == 0) {
    return;
  }

  if (!command.startsWith("SET PWM")) {
    return;
  }

  int pwmIndex = command.indexOf("PWM");
  int dirIndex = command.indexOf("DIR");
  if (pwmIndex < 0 || dirIndex < 0) {
    return;
  }

  String pwmText = command.substring(pwmIndex + 3, dirIndex);
  String directionText = command.substring(dirIndex + 3);
  pwmText.trim();
  directionText.trim();

  int requestedPwm = pwmText.toInt();
  requestedPwm = constrain(requestedPwm, 0, 255);
  pwmCommand = requestedPwm;

  heating = directionText.equalsIgnoreCase("HEAT");
  applyOutput();
}

void setup() {
  pinMode(H_BRIDGE_PIN_A, OUTPUT);
  pinMode(H_BRIDGE_PIN_B, OUTPUT);

  analogWrite(H_BRIDGE_PIN_A, 0);
  analogWrite(H_BRIDGE_PIN_B, 0);

  Serial.begin(115200);
  Serial.println("Arduino ready. Use: SET PWM 120 DIR HEAT");
}

void loop() {
  if (Serial.available() > 0) {
    String incoming = Serial.readStringUntil('\n');
    parseCommand(incoming);
  }

  float temperatureC = readTemperatureC();

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
  Serial.print(", Heat/Cool: ");
  Serial.println(heating ? 1 : 0);

  delay(100);
}
