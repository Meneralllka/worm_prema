#include <Bluepad32.h>
#include <ESP32Servo.h> 

#define AIN1 33 
#define AIN2 32 
#define PWMA 27 

const int SERVO_REST = 90;     
const int LIFT_SIDE = -1; 
const int LIFT_ANGLE_UP = 180; // Neck and Head target
const int LIFT_ANGLE_TAIL = 0; // Tail target as requested
const int STICK_DEADZONE = 25;

Servo servos[4]; 
int pins[] = {5, 18, 19, 21}; // 0:Tail, 1:Lower-Mid, 2:Neck, 3:Head

float phase = 0; 
float lag = 1.0;

// --- Toggle States ---
bool tailLifted = false;  // A Button
bool neckLifted = false;  // Y Button
bool headLifted = false;  // X Button

bool aWasPressed = false; 
bool xWasPressed = false; 
bool yWasPressed = false; 

ControllerPtr myControllers[BP32_MAX_GAMEPADS];

void setup() {
    Serial.begin(115200);
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);

    for(int i = 0; i < 4; i++) {
        servos[i].attach(pins[i], 500, 2500); 
        servos[i].write(SERVO_REST); 
    }

    pinMode(AIN1, OUTPUT); pinMode(AIN2, OUTPUT); pinMode(PWMA, OUTPUT);
    BP32.setup(&onConnectedController, &onDisconnectedController);
}

void loop() {
    BP32.update();
    ControllerPtr ctl = myControllers[0];

    if (ctl && ctl->isConnected()) {
        // --- Toggle Handling ---
        if (ctl->a() && !aWasPressed) tailLifted = !tailLifted;
        if (ctl->x() && !xWasPressed) headLifted = !headLifted;
        if (ctl->y() && !yWasPressed) neckLifted = !neckLifted;
        
        // --- Global Reset (Left Stick Click) ---
        if (ctl->thumbL()) {
            tailLifted = false;
            neckLifted = false;
            headLifted = false;
        }

        aWasPressed = ctl->a();
        xWasPressed = ctl->x();
        yWasPressed = ctl->y();

        int stickY = ctl->axisY(); 

        if (abs(stickY) > STICK_DEADZONE) {
            float amp = map(abs(stickY), STICK_DEADZONE, 512, 0, 60);
            float currentSpeed = map(abs(stickY), STICK_DEADZONE, 512, 5, 40) / 100.0;
            
            if (stickY < 0) phase -= currentSpeed; 
            else            phase += currentSpeed;

            updateServos(amp);
        } 
        else {
            // Idle positions (Maintains toggled poses)
            servos[0].write(tailLifted ? LIFT_ANGLE_TAIL : SERVO_REST);
            servos[1].write(SERVO_REST);
            servos[2].write(neckLifted ? LIFT_ANGLE_UP : SERVO_REST);
            servos[3].write(headLifted ? LIFT_ANGLE_UP : SERVO_REST);
        }

        // Pump Control
        bool lb = ctl->l1(); bool rb = ctl->r1();
        digitalWrite(AIN1, lb && !rb);
        digitalWrite(AIN2, !lb && rb);
        analogWrite(PWMA, (lb || rb) ? 255 : 0);
    }
    delay(20); 
}

void updateServos(float amp) {
    for(int i = 0; i < 4; i++) {
        bool isLifted = false;
        int targetAngle = SERVO_REST;

        if (i == 0 && tailLifted) { isLifted = true; targetAngle = LIFT_ANGLE_TAIL; }
        if (i == 2 && neckLifted) { isLifted = true; targetAngle = LIFT_ANGLE_UP; }
        if (i == 3 && headLifted) { isLifted = true; targetAngle = LIFT_ANGLE_UP; }

        if (isLifted) {
            servos[i].write(targetAngle);
        } else {
            float wave = sin(phase + (i * lag)) * amp;
            float lift = max(0.0f, wave);
            servos[i].write(SERVO_REST + (lift * LIFT_SIDE));
        }
    }
}

void onConnectedController(ControllerPtr ctl) { if (myControllers[0] == nullptr) myControllers[0] = ctl; }
void onDisconnectedController(ControllerPtr ctl) { if (myControllers[0] == ctl) myControllers[0] = nullptr; }
