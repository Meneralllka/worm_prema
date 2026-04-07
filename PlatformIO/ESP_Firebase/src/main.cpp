#include <Arduino.h>
#include <WiFi.h>
#include <Bluepad32.h>
#include <ESP32Servo.h> 
#include <math.h>

// --- Function Prototypes ---
void updateServos();
void onConnectedController(ControllerPtr ctl);
void onDisconnectedController(ControllerPtr ctl);
void tcpServerTaskCode(void * parameter); 

// --- 1. Hotspot Wi-Fi Credentials ---
const char* ssid = "Galaxy S24 Ultra D870"; 
const char* password = "12345678";

// --- 2. TCP Server Setup ---
const int TCP_PORT = 8080;
WiFiServer server(TCP_PORT);
TaskHandle_t TCPServerTask;

// --- 3. Hardware Pins ---
#define AIN1 33 
#define AIN2 32 
#define PWMA 27 

// --- Sensor Pins ---
#define PIN_VOLTAGE 36 // VP
#define PIN_CURRENT 39 // VN

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
volatile float fb_lag = 1.2;
volatile float fb_power = 1.0;

// Telemetry Variables to share between loop() and the TCP Task
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

    server.begin();
    xTaskCreatePinnedToCore(tcpServerTaskCode, "TCPServerTask", 10000, NULL, 1, &TCPServerTask, 0);                  
    BP32.setup(&onConnectedController, &onDisconnectedController);
}

void tcpServerTaskCode(void * parameter) {
    unsigned long lastTelemetryTime = 0;

    for(;;) {
        WiFiClient client = server.available(); 
        
        if (client) {
            Serial.println("New TCP Client Connected");
            client.setTimeout(50); 
            
            while (client.connected()) {
                // 1. Check for incoming slider data from Python
                if (client.available()) {
                    String request = client.readStringUntil('\n');
                    request.trim(); 
                    
                    if (request.length() > 0) {
                        int colonIndex = request.indexOf(':');
                        if (colonIndex != -1) {
                            String key = request.substring(0, colonIndex);
                            float value = request.substring(colonIndex + 1).toFloat();
                            
                            if (key == "amplitude") fb_amplitude = value;
                            else if (key == "lag") fb_lag = value;
                            else if (key == "power") fb_power = value;
                            
                            Serial.printf("Updated -> %s: %.2f\n", key.c_str(), value);
                        }
                    }
                }

                // 2. Push telemetry data to Python every 500ms
                unsigned long currentMillis = millis();
                if (currentMillis - lastTelemetryTime >= 50) {
                    lastTelemetryTime = currentMillis;
                    // Format: "telemetry:voltage:current\n"
                    client.printf("telemetry:%.2f:%.2f\n", sensor_voltage_out, sensor_current_out);
                }

                vTaskDelay(10 / portTICK_PERIOD_MS); 
            }
            client.stop();
            Serial.println("TCP Client Disconnected");
        }
        vTaskDelay(200 / portTICK_PERIOD_MS); 
    }
}

void loop() {
    BP32.update();
    ControllerPtr ctl = myControllers[0];

    // --- Sensor Reading & Printing ---
    unsigned long currentTime = millis();
    if (currentTime - lastPrintTime >= printInterval) {
        lastPrintTime = currentTime;

        // Current Sensor (ACS712)
        // --- Current Sensor (ACS712) ---
        float currentPinV = analogRead(PIN_CURRENT) * (3.3 / 4095.0);
        
        // Linear best-fit calculation
        sensor_current_out = (1.5 - currentPinV)/0.1;//(0.7995 * currentPinV) - 1.0931;

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
            float currentSpeed = 0.2; 
            if (stickY < 0) phase -= currentSpeed; 
            else            phase += currentSpeed;

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