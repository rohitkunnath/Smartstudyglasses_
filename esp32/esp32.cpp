#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

WebServer server(80);

const int VIB_PIN = 13;
bool vibrating = false;

void handleRoot() {
  server.send(200, "text/plain", "ESP32 Vibrator Server");
}

void handleVibrateOn() {
  digitalWrite(VIB_PIN, HIGH);
  vibrating = true;
  server.send(200, "text/plain", "VIBRATE ON");
}

void handleVibrateOff() {
  digitalWrite(VIB_PIN, LOW);
  vibrating = false;
  server.send(200, "text/plain", "VIBRATE OFF");
}

void setup() {
  Serial.begin(115200);
  pinMode(VIB_PIN, OUTPUT);
  digitalWrite(VIB_PIN, LOW);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
  }
  server.on("/", handleRoot);
  server.on("/vibrate/on", handleVibrateOn);
  server.on("/vibrate/off", handleVibrateOff);
  server.begin();
}

void loop() {
  server.handleClient();
}
