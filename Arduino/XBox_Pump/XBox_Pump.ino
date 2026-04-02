#include <Bluepad32.h>

#define AIN1 19 // Motor A Input 1
#define AIN2 18 // Motor A Input 2
#define PWMA 5 // Motor A PWM

#define BIN1 21 // Motor A Input 1
#define BIN2 22 // Motor A Input 2
#define PWMB 23 // Motor A PWM

ControllerPtr myControllers[BP32_MAX_GAMEPADS];

void onConnectedController(ControllerPtr ctl) {
    if (myControllers[0] == nullptr) {
        Serial.println("Xbox Controller Connected!");
        myControllers[0] = ctl;
    }
}

void onDisconnectedController(ControllerPtr ctl) {
    if (myControllers[0] == ctl) {
        Serial.println("Xbox Controller Disconnected!");
        myControllers[0] = nullptr;
    }
}

void setup() {
    pinMode(AIN1, OUTPUT);
    pinMode(AIN2, OUTPUT);
    pinMode(PWMA, OUTPUT);

    pinMode(BIN1, OUTPUT);
    pinMode(BIN2, OUTPUT);
    pinMode(PWMB, OUTPUT);

    Serial.begin(115200);
    BP32.setup(&onConnectedController, &onDisconnectedController);
}

void loop() {
    BP32.update();
    ControllerPtr ctl = myControllers[0];

    if (ctl && ctl->isConnected()) {

        // --- BUTTONS (Boolean) ---
        bool a = ctl->a();
        bool b = ctl->b();
        bool x = ctl->x();
        bool y = ctl->y();

    
        // Output to Serial Monitor for debugging
        //Serial.printf("BTN: A:%d B:%d X:%d Y:%d \n",
          //            a, b, x, y);
        if (a && !b){
          Serial.println("Pump 1 fwd");
          digitalWrite(AIN1, 1);
          digitalWrite(AIN2, 0);
          analogWrite(PWMA, 255);
        } else if (!a && b){
          Serial.println("Pump 1 bwd");
          digitalWrite(AIN1, 0);
          digitalWrite(AIN2, 1);
          analogWrite(PWMA, 255);
        } else if (!a && !b){
          Serial.println("Pump 1 off");
          digitalWrite(AIN1, 0);
          digitalWrite(AIN2, 0);
          analogWrite(PWMA, 0);
        }  
        if (x && !y){
          Serial.println("Pump 2 fwd");
          digitalWrite(BIN1, 1);
          digitalWrite(BIN2, 0);
          analogWrite(PWMB, 255);
        } else if (!x && y){
          Serial.println("Pump 2 bwd");
          digitalWrite(BIN1, 0);
          digitalWrite(BIN2, 1);
          analogWrite(PWMB, 255);
        } else if (!x && !y) {
          Serial.println("Pump 2 off");
          digitalWrite(BIN1, 0);
          digitalWrite(BIN2, 0);
          analogWrite(PWMB, 0);
        } 
    }
    delay(10);
}
