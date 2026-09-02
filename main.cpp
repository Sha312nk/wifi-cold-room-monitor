#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_AHTX0.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Optional OLED libraries
#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>

// ================== CONFIGURATION ==================
const char* ssid = "WIFI NAME";          // <-- change
const char* password = "WIFI PASSWORD";  // <-- change
const char* serverUrl = "http://192.168.120.145:5000/data"; // <-- your laptop's IP

// ================== OBJECTS ==================
Adafruit_AHTX0 aht;

// Optional OLED – adjust I2C address if needed (0x3C or 0x3D)
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// Onboard LED (usually GPIO2)
const int ledPin = 2;

// Timing
unsigned long lastSend = 0;
const unsigned long sendInterval = 10000; // 10 seconds

// ================== SMOOTHING FILTER ==================
const int numReadings = 5;            // Number of samples to average
float humReadings[numReadings];
float tempReadings[numReadings];
int readIndex = 0;
float humTotal = 0;
float tempTotal = 0;
float humAverage = 0;
float tempAverage = 0;

// ================== FUNCTION PROTOTYPES ==================
void readAndSendData();

// ================== SETUP ==================
void setup() {
  Serial.begin(115200);
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);

  // Initialize I2C (SDA=21, SCL=22)
  Wire.begin(21, 22);
  delay(100);   // let sensor power stabilize

  // Initialize AHT10 sensor
  if (!aht.begin()) {
    Serial.println("Could not find AHT10 sensor! Check wiring.");
    while (1) delay(1000); // halt
  }
  Serial.println("AHT10 initialized.");

  // Initialize OLED (optional)
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED not found, continuing without it.");
  } else {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("Cold Room Monitor");
    display.display();
  }

  // Initialize smoothing arrays
  for (int i = 0; i < numReadings; i++) {
    humReadings[i] = 0;
    tempReadings[i] = 0;
  }

  // Connect to Wi-Fi
  Serial.print("Connecting to Wi-Fi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected! IP: " + WiFi.localIP().toString());
}

// ================== LOOP ==================
void loop() {
  if (millis() - lastSend >= sendInterval) {
    lastSend = millis();
    readAndSendData();
  }
}

// ================== FUNCTIONS ==================
void readAndSendData() {
  sensors_event_t humidity, temp;
  aht.getEvent(&humidity, &temp); // populate temp and humidity objects

  float rawTemp = temp.temperature;
  float rawHum = humidity.relative_humidity;

  // Validate raw readings
  if (isnan(rawTemp) || isnan(rawHum) || rawTemp < -40 || rawTemp > 85 || rawHum < 0 || rawHum > 100) {
    Serial.println("Invalid sensor reading, skipping.");
    return;
  }

  // Add to smoothing arrays
  humTotal = humTotal - humReadings[readIndex];
  humReadings[readIndex] = rawHum;
  humTotal = humTotal + humReadings[readIndex];

  tempTotal = tempTotal - tempReadings[readIndex];
  tempReadings[readIndex] = rawTemp;
  tempTotal = tempTotal + tempReadings[readIndex];

  readIndex = (readIndex + 1) % numReadings;

  // Compute averages
  humAverage = humTotal / numReadings;
  tempAverage = tempTotal / numReadings;

  // Display on OLED if available
  if (display.getBuffer() != NULL) {
    display.clearDisplay();
    display.setCursor(0, 0);
    display.print("Temp: ");
    display.print(tempAverage, 1);
    display.print(" C");
    display.setCursor(0, 20);
    display.print("Hum : ");
    display.print(humAverage, 1);
    display.print(" %");
    display.display();
  }

  // Create JSON payload with averaged values
  StaticJsonDocument<200> doc;
  doc["temp"] = tempAverage;
  doc["humidity"] = humAverage;
  String jsonString;
  serializeJson(doc, jsonString);

  // Send HTTP POST
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    int httpCode = http.POST(jsonString);

    if (httpCode > 0) {
      Serial.printf("POST success, code: %d\n", httpCode);
      // Blink LED
      digitalWrite(ledPin, HIGH);
      delay(100);
      digitalWrite(ledPin, LOW);
    } else {
      Serial.printf("POST failed, error: %s\n", http.errorToString(httpCode).c_str());
    }
    http.end();
  } else {
    Serial.println("Wi-Fi disconnected, attempting reconnect...");
    WiFi.reconnect();
  }
}