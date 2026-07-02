#include <Arduino.h>
#include <WiFi.h>
#include <Bluepad32.h>
#include <ESP32Servo.h> 
#include <math.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h> // NEW: For dynamic UI configuration

// --- Function Prototypes ---
void updateServos();
void onConnectedController(ControllerPtr ctl);
void onDisconnectedController(ControllerPtr ctl);
void webSocketTaskCode(void * parameter); 
void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length);
void sendConfiguration(uint8_t num); // NEW: Handshake protocol

// --- 1. Hotspot Wi-Fi Credentials ---
const char* ssid = "Galaxy S24 Ultra D870"; 
const char* password = "12345678";

// --- 2. WebSocket Server Setup ---
const int WS_PORT = 8080;
WebSocketsServer webSocket = WebSocketsServer(WS_PORT);
TaskHandle_t WSTask;

// --- 3. Hardware Pins ---
#define AIN1 33 
#define AIN2 32 
#define PWMA 27 

// --- Sensor Pins ---
#define PIN_VOLTAGE 39 // VP
#define PIN_CURRENT 36 // VN

const int SERVO_REST = 90;     
const int LIFT_SIDE = -1; 
const int LIFT_ANGLE_UP = 180; 
const int LIFT_ANGLE_TAIL = 0; 
const int TAIL_B_ANGLE = 135; 
const int STICK_DEADZONE = 25;

Servo servos[4]; 
int pins[] = {5, 18, 19, 21}; 

// --- State Variables ---
float phase = 0; 

volatile float fb_amplitude = 70.0;
volatile float fb_lag = 0.8;
volatile float fb_power = 1.0;
volatile float fb_frequency = 0.2; 

// Telemetry Variables to share between loop() and the WebSocket Task
volatile float sensor_voltage_out = 0.0;
volatile float sensor_current_out = 0.0;

// Toggles
bool tailLifted = false;  
bool neckLifted = false;  
bool headLifted = false;  
bool tailAt135 = false;   
bool aWasPressed = false; 
bool bWasPressed = false; 
bool xWasPressed = false; 
bool yWasPressed = false; 

// Sensor Print Timer
unsigned long lastPrintTime = 0;
const int printInterval = 50; 

ControllerPtr myControllers[BP32_MAX_GAMEPADS];

void setup() {
    Serial.begin(115200);
    analogReadResolution(12);

    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);

    for(int i = 0; i < 4; i++) {
        servos[i].attach(pins[i], 500, 2500); 
        servos[i].write(SERVO_REST); 
    }
    pinMode(AIN1, OUTPUT); pinMode(AIN2, OUTPUT); pinMode(PWMA, OUTPUT);

    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) { 
        delay(500); 
        Serial.print("."); 
    }
    
    Serial.println("\nWiFi Connected!");
    Serial.print("ESP32 IP Address: ");
    Serial.println(WiFi.localIP()); 

    // Initialize WebSocket Server
    webSocket.begin();
    webSocket.onEvent(webSocketEvent);

    // Create RTOS task to handle WebSockets asynchronously
    xTaskCreatePinnedToCore(webSocketTaskCode, "WSTask", 10000, NULL, 1, &WSTask, 0);                  
    BP32.setup(&onConnectedController, &onDisconnectedController);
}

// --- Dynamic Configuration Handshake ---
void sendConfiguration(uint8_t num) {
    StaticJsonDocument<1024> doc;
    
    // --- 1. Define UI Sliders ---
    JsonArray sliders = doc.createNestedArray("sliders");
    
    JsonObject s1 = sliders.createNestedObject();
    s1["id"] = "amplitude"; s1["label"] = "Amplitude"; 
    s1["min"] = 0; s1["max"] = 100; s1["val"] = 70; s1["scale"] = 1.0;
    
    JsonObject s2 = sliders.createNestedObject();
    s2["id"] = "lag"; s2["label"] = "Phase Lag"; 
    s2["min"] = 0; s2["max"] = 200; s2["val"] = 80; s2["scale"] = 0.01; // 80 * 0.01 = 0.8
    
    JsonObject s3 = sliders.createNestedObject();
    s3["id"] = "power"; s3["label"] = "Wave Power"; 
    s3["min"] = 10; s3["max"] = 300; s3["val"] = 100; s3["scale"] = 0.01; // 100 * 0.01 = 1.0
    
    JsonObject s4 = sliders.createNestedObject();
    s4["id"] = "frequency"; s4["label"] = "Frequency"; 
    s4["min"] = 1; s4["max"] = 100; s4["val"] = 20; s4["scale"] = 0.01; // 20 * 0.01 = 0.2

    // --- 2. Define Telemetry Layout ---
    JsonArray telemetry = doc.createNestedArray("telemetry");
    telemetry.add("Voltage (V)");
    telemetry.add("Current (A)");

    String configStr;
    serializeJson(doc, configStr);
    String payload = "CONFIG:" + configStr;
    webSocket.sendTXT(num, payload);
}

// --- WebSocket Event Handler ---
void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.printf("[%u] WebSocket Client Disconnected\n", num);
            break;
            
        case WStype_CONNECTED: {
            IPAddress ip = webSocket.remoteIP(num);
            Serial.printf("[%u] WebSocket Client Connected from %d.%d.%d.%d\n", num, ip[0], ip[1], ip[2], ip[3]);
            sendConfiguration(num); // Trigger the UI build
            break;
        }
            
        case WStype_TEXT: {
            String request = String((char*)payload);
            request.trim(); 
            
            // Handle SET format from new UI (e.g., SET:frequency:0.25)
            if (request.startsWith("SET:")) {
                int firstColon = request.indexOf(':');
                int secondColon = request.indexOf(':', firstColon + 1);
                
                if (firstColon != -1 && secondColon != -1) {
                    String key = request.substring(firstColon + 1, secondColon);
                    float value = request.substring(secondColon + 1).toFloat();
                    
                    if (key == "amplitude") fb_amplitude = value;
                    else if (key == "lag") fb_lag = value;
                    else if (key == "power") fb_power = value;
                    else if (key == "frequency") fb_frequency = value; 
                    
                    Serial.printf("Updated -> %s: %.2f\n", key.c_str(), value);
                }
            }
            break;
        }
    }
}

// --- WebSocket RTOS Task ---
void webSocketTaskCode(void * parameter) {
    unsigned long lastTelemetryTime = 0;

    for(;;) {
        webSocket.loop(); 

        unsigned long currentMillis = millis();
        if (currentMillis - lastTelemetryTime >= 50) {
            lastTelemetryTime = currentMillis;
            
            // Format strictly as required by the new website UI: DATA:<timestamp>,<val1>,<val2>
            char msg[64];
            snprintf(msg, sizeof(msg), "DATA:%lu,%.2f,%.2f", currentMillis, sensor_voltage_out, sensor_current_out);
            
            webSocket.broadcastTXT(msg);
        }

        vTaskDelay(10 / portTICK_PERIOD_MS); 
    }
}

void loop() {
    BP32.update();
    ControllerPtr ctl = myControllers[0];

    // --- Sensor Reading & Printing ---
    unsigned long currentTime = millis();
    if (currentTime - lastPrintTime >= printInterval) {
        lastPrintTime = currentTime;

        // --- Current Sensor (ACS712) ---
        float currentPinV = analogRead(PIN_CURRENT) * (3.3 / 4095.0);
        
        // Linear best-fit calculation
        sensor_current_out = (1.5 - currentPinV)/0.1;

        // Voltage Sensor
        float voltagePinV = analogRead(PIN_VOLTAGE) * (3.3 / 4095.0);
        sensor_voltage_out = (voltagePinV * (1.0 / 0.199)) + 0.975; 

        Serial.printf("Current: %.2f A | Voltage: %.2f V\n", sensor_current_out, sensor_voltage_out);
    }

    if (ctl && ctl->isConnected()) {

        if (ctl->a() && !aWasPressed) tailLifted = !tailLifted;
        if (ctl->b() && !bWasPressed) tailAt135 = !tailAt135; 
        if (ctl->x() && !xWasPressed) headLifted = !headLifted;
        if (ctl->y() && !yWasPressed) neckLifted = !neckLifted;
        
        if (ctl->thumbL()) {
            tailLifted = false; tailAt135 = false; neckLifted = false; headLifted = false;
        }

        aWasPressed = ctl->a(); bWasPressed = ctl->b(); xWasPressed = ctl->x(); yWasPressed = ctl->y();

        int stickY = ctl->axisY(); 

        if (abs(stickY) > STICK_DEADZONE) {
            if (stickY < 0) phase -= fb_frequency; 
            else            phase += fb_frequency;

            updateServos();
        } 
        else {
            if (tailAt135) servos[0].write(TAIL_B_ANGLE);
            else servos[0].write(tailLifted ? LIFT_ANGLE_TAIL : SERVO_REST);
            
            servos[1].write(SERVO_REST);
            servos[2].write(neckLifted ? LIFT_ANGLE_UP : SERVO_REST);
            servos[3].write(headLifted ? LIFT_ANGLE_UP : SERVO_REST);
        }

        bool lb = ctl->l1(); bool rb = ctl->r1();
        digitalWrite(AIN1, lb && !rb);
        digitalWrite(AIN2, !lb && rb);
        analogWrite(PWMA, (lb || rb) ? 255 : 0);
    }
    delay(20); 
}

void updateServos() {
    for(int i = 0; i < 4; i++) {
        bool isManual = false;
        int targetAngle = SERVO_REST;

        if (i == 0) {
            if (tailAt135) { isManual = true; targetAngle = TAIL_B_ANGLE; }
            else if (tailLifted) { isManual = true; targetAngle = LIFT_ANGLE_TAIL; }
        }
        if (i == 2 && neckLifted) { isManual = true; targetAngle = LIFT_ANGLE_UP; }
        if (i == 3 && headLifted) { isManual = true; targetAngle = LIFT_ANGLE_UP; }

        if (isManual) {
            servos[i].write(targetAngle);
        } else {
            float p_i = phase + (i * fb_lag);
            float s = sin(p_i);
            float sgn = (s >= 0) ? 1.0 : -1.0;         
            float wave = sgn * pow(abs(s), fb_power) * fb_amplitude;
            
            float lift = max(0.0f, wave); 
            servos[i].write(SERVO_REST + (lift * LIFT_SIDE));
        }
    }
}

void onConnectedController(ControllerPtr ctl) { if (myControllers[0] == nullptr) myControllers[0] = ctl; }
void onDisconnectedController(ControllerPtr ctl) { if (myControllers[0] == ctl) myControllers[0] = nullptr; }