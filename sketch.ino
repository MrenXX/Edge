/*
  Eco-Edge — INSAT Re·Tech Fusion, Part 1
  Wokwi: MPU6050 @ 0x69, DS1307, pot on 34 as rough "amps", LEDs 4 (green) / 2 (red).
  MQTT JSON every ~2s; ring buffer if broker drops; TCP reset + MQTT backoff on failures.
*/

#define MQTT_MAX_PACKET_SIZE 2048

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <RTClib.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <cstdio>
#include <cmath>
#include <cstring>

// backlog when mqtt dies or publish() fails (hackathon bonus)
static const int RING_SLOTS = 8;
static const int RING_MSG = 768;
static char ringBuf[RING_SLOTS][RING_MSG];
static int ringHead = 0;
static int ringCount = 0;

// pins = diagram.json
static const int PIN_I2C_SDA = 21;
static const int PIN_I2C_SCL = 22;
static const uint8_t MPU_I2C_ADDR = 0x69;  // AD0 pulled high

static const int PIN_LED_GREEN = 4;
static const int PIN_LED_RED = 2;
static const int PIN_POT_ADC = 34;

// change for your wifi / broker
static const char *WIFI_SSID = "Wokwi-GUEST";
static const char *WIFI_PASSWORD = "";

static const char *MQTT_HOST = "broker.hivemq.com";
static const uint16_t MQTT_PORT = 1883;
static const char *MQTT_TOPIC = "telemetry/ADWYA-CHILLER-01";
static const char *DEVICE_ID = "ADWYA-CHILLER-01";

static const unsigned long PUBLISH_INTERVAL_MS = 2000;
static const float POT_AMPS_MIN = 0.0f;
static const float POT_AMPS_MAX = 20.0f;

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
RTC_DS1307 rtc;
Adafruit_MPU6050 mpu;

static void resetMqttTcp() {
  mqtt.disconnect();
  wifiClient.stop();
}

static void ringPush(const char *msg) {
  if (ringCount == RING_SLOTS) {
    ringHead = (ringHead + 1) % RING_SLOTS;
    ringCount--;
    Serial.println("[buffer] full, dropped oldest");
  }
  int slot = (ringHead + ringCount) % RING_SLOTS;
  strncpy(ringBuf[slot], msg, RING_MSG - 1);
  ringBuf[slot][RING_MSG - 1] = '\0';
  ringCount++;
  Serial.printf("[buffer] queued (%d in buffer)\n", ringCount);
}

static void ringFlush() {
  while (mqtt.connected() && ringCount > 0) {
    const char *msg = ringBuf[ringHead];
    for (int i = 0; i < 4; i++) {
      mqtt.loop();
      delay(2);
    }
    if (mqtt.publish(MQTT_TOPIC, msg, false)) {
      Serial.printf("[buffer] flushed (%d left)\n", ringCount - 1);
      ringHead = (ringHead + 1) % RING_SLOTS;
      ringCount--;
      delay(25);
    } else {
      resetMqttTcp();
      break;
    }
  }
}

static bool mpuOk = false;
static bool rtcOk = false;

static inline float potToAmps(int raw12) {
  float t = raw12 / 4095.0f;
  if (t < 0.0f) t = 0.0f;
  if (t > 1.0f) t = 1.0f;
  return POT_AMPS_MIN + t * (POT_AMPS_MAX - POT_AMPS_MIN);
}

static void formatTimestamp(char *out, size_t outLen) {
  if (!rtcOk) {
    snprintf(out, outLen, "1970-01-01T00:00:00.000Z");
    return;
  }
  DateTime now = rtc.now();
  snprintf(out, outLen, "%04u-%02u-%02uT%02u:%02u:%02u.000+01:00",
           now.year(), now.month(), now.day(), now.hour(), now.minute(), now.second());
}

static bool connectWifi() {
  Serial.print("WiFi: connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi: FAILED");
    return false;
  }
  Serial.print("WiFi: OK, IP ");
  Serial.println(WiFi.localIP());
  return true;
}

// one shot connect, no while() blocking wokwi
static bool tryMqttConnect() {
  if (mqtt.connected()) {
    return true;
  }
  Serial.print("MQTT: connecting... ");
  String clientId = String("ecoedge-") + String((uint32_t)ESP.getEfuseMac(), HEX);
  if (mqtt.connect(clientId.c_str())) {
    Serial.println("OK");
    for (int i = 0; i < 10; i++) {
      mqtt.loop();
      delay(5);
    }
    ringFlush();
    return true;
  }
  Serial.print("fail rc=");
  Serial.println(mqtt.state());
  resetMqttTcp();
  return false;
}

static bool buildPayload(char *out, size_t outLen, bool *edgeAnomalyOut) {
  char ts[40];
  formatTimestamp(ts, sizeof(ts));

  sensors_event_t a, g, tempEv;
  float ax = 0, ay = 0, az = 1.0f, gx = 0, gy = 0, gz = 0, tempC = 25.0f;

  if (mpuOk) {
    mpu.getEvent(&a, &g, &tempEv);
    const float g0 = 9.80665f;
    ax = a.acceleration.x / g0;
    ay = a.acceleration.y / g0;
    az = a.acceleration.z / g0;
    const float rad2deg = 57.2957795f;
    gx = g.gyro.x * rad2deg;
    gy = g.gyro.y * rad2deg;
    gz = g.gyro.z * rad2deg;
    tempC = tempEv.temperature;
    if (isnan(tempC) || isinf(tempC)) tempC = 25.0f;
  }

  int potRaw = analogRead(PIN_POT_ADC);
  float amps = potToAmps(potRaw);

  float amag = sqrtf(ax * ax + ay * ay + az * az);
  float gmag = sqrtf(gx * gx + gy * gy + gz * gz);
  bool edge = (fabsf(amag - 1.0f) > 0.45f) || (gmag > 80.0f) || (amps > 17.5f);
  *edgeAnomalyOut = edge;

  int n = snprintf(
      out, outLen,
      "{\"timestamp\":\"%s\",\"device_id\":\"%s\",\"sensors\":{"
      "\"accel_x_g\":%.4f,\"accel_y_g\":%.4f,\"accel_z_g\":%.4f,"
      "\"gyro_x_dps\":%.2f,\"gyro_y_dps\":%.2f,\"gyro_z_dps\":%.2f,"
      "\"temp_c\":%.2f,\"current_amps\":%.3f},\"edge_anomaly\":%s,"
      "\"meta\":{\"fw\":\"wokwi-1.0.0\",\"uptime_s\":%lu}}",
      ts, DEVICE_ID, (double)ax, (double)ay, (double)az, (double)gx, (double)gy, (double)gz,
      (double)tempC, (double)amps, edge ? "true" : "false",
      (unsigned long)(millis() / 1000UL));
  if (n <= 0 || (size_t)n >= outLen) {
    return false;
  }
  return true;
}

static void setLeds(bool wifiOk, bool mqttOk, bool anomaly) {
  if (anomaly) {
    digitalWrite(PIN_LED_RED, HIGH);
    digitalWrite(PIN_LED_GREEN, LOW);
    return;
  }
  digitalWrite(PIN_LED_RED, LOW);
  digitalWrite(PIN_LED_GREEN, (wifiOk && mqttOk) ? HIGH : LOW);
}

void setup() {
  Serial.begin(115200);
  delay(800);

  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_RED, HIGH);
  delay(200);
  digitalWrite(PIN_LED_RED, LOW);

#if defined(ADC_ATTEN_DB_11)
  analogSetAttenuation(ADC_ATTEN_DB_11);
#elif defined(ADC_11db)
  analogSetAttenuation(ADC_11db);
#endif
  analogReadResolution(12);

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  Wire.setClock(100000);

  rtcOk = rtc.begin();
  if (!rtcOk) {
    Serial.println("RTC: not found (check DS1307 wiring / I2C)");
  } else {
    // DS1307: no lostPower() — if year garbage, stamp once from compile time
    DateTime now = rtc.now();
    if (now.year() < 2020 || now.year() > 2038) {
      Serial.println("RTC: invalid date — setting compile time once");
      rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
    }
  }

  mpuOk = mpu.begin(MPU_I2C_ADDR, &Wire, 0);
  if (!mpuOk) {
    Serial.println("MPU6050: not found at 0x69 (check AD0->3V3 and wiring)");
  } else {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    Serial.println("MPU6050: OK @ 0x69");
  }

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(2048);

  if (!connectWifi()) {
    Serial.println("Boot: WiFi failed — will retry in loop");
  }

  Serial.println("Setup done.");
}

void loop() {
  static unsigned long lastPub = 0;
  static bool lastAnomaly = false;
  static bool prevWifiOk = false;
  static unsigned long lastMqttTry = 0;
  static unsigned long mqttBackoffMs = 2500UL;
  const unsigned long MQTT_BACKOFF_INITIAL = 2500UL;
  const unsigned long MQTT_BACKOFF_MAX = 30000UL;

  bool wifiOk = (WiFi.status() == WL_CONNECTED);
  if (!wifiOk) {
    connectWifi();
    wifiOk = (WiFi.status() == WL_CONNECTED);
  }

  if (wifiOk && !prevWifiOk) {
    mqttBackoffMs = MQTT_BACKOFF_INITIAL;
    lastMqttTry = 0;
  }
  prevWifiOk = wifiOk;

  if (wifiOk && !mqtt.connected()) {
    unsigned long now = millis();
    if (lastMqttTry == 0 || now - lastMqttTry >= mqttBackoffMs) {
      lastMqttTry = now;
      if (tryMqttConnect()) {
        mqttBackoffMs = MQTT_BACKOFF_INITIAL;
      } else {
        mqttBackoffMs *= 2;
        if (mqttBackoffMs > MQTT_BACKOFF_MAX) {
          mqttBackoffMs = MQTT_BACKOFF_MAX;
        }
      }
    }
  }

  if (wifiOk && mqtt.connected()) {
    ringFlush();
  }

  bool anomaly = false;
  char payload[768];

  if (millis() - lastPub >= PUBLISH_INTERVAL_MS) {
    lastPub = millis();
    if (!buildPayload(payload, sizeof(payload), &anomaly)) {
      Serial.println("JSON: build failed");
    } else {
      lastAnomaly = anomaly;
      if (mqtt.connected()) {
        for (int i = 0; i < 5; i++) {
          mqtt.loop();
          delay(2);
        }
        size_t len = strlen(payload);
        if (!mqtt.publish(MQTT_TOPIC, payload, false)) {
          Serial.printf("MQTT publish failed len=%u state=%d\n", (unsigned)len, mqtt.state());
          resetMqttTcp();
          ringPush(payload);
        } else {
          Serial.println(payload);
        }
      } else {
        ringPush(payload);
        Serial.println("MQTT: offline, queued to buffer");
      }
    }
  }

  bool mqttOk = mqtt.connected();
  setLeds(wifiOk, mqttOk, lastAnomaly);
  mqtt.loop();
  delay(5);
}
