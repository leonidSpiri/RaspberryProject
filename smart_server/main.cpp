#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#define FAN_PIN D1
#define COND_PIN D2
#define MOTION_PIN D3
#define ONE_WIRE_BUS D4

const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";
const String baseUrl = "http://192.168.1.122:9888/api/";

WiFiClient client;
HTTPClient http;
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

int roomTempSensorIndex = 0;
int boxTempSensorIndex = 1;

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected");

  pinMode(FAN_PIN, OUTPUT);
  pinMode(COND_PIN, OUTPUT);
  pinMode(MOTION_PIN, INPUT);
  digitalWrite(FAN_PIN, LOW);
  digitalWrite(COND_PIN, LOW);

  sensors.begin();
}

void retrieveDataFromServer() {
  if (WiFi.status() == WL_CONNECTED) {
    http.begin(client, baseUrl + "mobile/last_request");
    int httpCode = http.GET();
    if (httpCode > 0) {
      String payload = http.getString();
      int idx = 0;
      while ((idx = payload.indexOf(",")) > 0) {
        String pair = payload.substring(0, idx);
        payload = payload.substring(idx + 1);
        int sep = pair.indexOf(":");
        int pin = pair.substring(0, sep).toInt();
        bool state = pair.substring(sep + 1) == "true";
        digitalWrite(pin, state ? HIGH : LOW);
      }
    }
    http.end();
  }
}

int readTemp(int index) {
  sensors.requestTemperatures();
  return (int)sensors.getTempCByIndex(index);
}

bool readMotion() {
  return digitalRead(MOTION_PIN);
}

void sendDataToServer() {
  if (WiFi.status() == WL_CONNECTED) {
    sensors.requestTemperatures();
    int roomTemp = readTemp(roomTempSensorIndex);
    int boxTemp = readTemp(boxTempSensorIndex);
    bool fanOn = digitalRead(FAN_PIN);
    bool condOn = digitalRead(COND_PIN);

    String json = "{\"newRequiredState\":\"1:" + String(fanOn) + ",2:" + String(condOn) + ",4:" + String(roomTemp) + ",5:" + String(boxTemp) + "\",";
    json += "\"isSecurityViolated\":" + String(readMotion() ? "true" : "false") + "}";

    http.begin(client, baseUrl + "rasp_state");
    http.addHeader("Content-Type", "application/json");
    int httpCode = http.POST(json);
    Serial.println(http.getString());
    http.end();
  }
}

unsigned long lastRetrieve = 0;
unsigned long lastSend = 0;
unsigned long lastSecurity = 0;

void loop() {
  unsigned long now = millis();

  if (now - lastRetrieve > 10000) {
    retrieveDataFromServer();
    lastRetrieve = now;
  }

  if (now - lastSend > 60000) {
    sendDataToServer();
    lastSend = now;
  }

  if (now - lastSecurity > 10000) {
    if (readMotion()) {
      if (WiFi.status() == WL_CONNECTED) {
        http.begin(client, baseUrl + "security/violated");
        http.POST("");
        http.end();
      }
      delay(30000);
    }
    lastSecurity = now;
  }
}
