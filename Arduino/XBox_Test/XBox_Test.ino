#include <Bluepad32.h>

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
    Serial.begin(115200);
    BP32.setup(&onConnectedController, &onDisconnectedController);
}

void loop() {
    BP32.update();
    ControllerPtr ctl = myControllers[0];

    if (ctl && ctl->isConnected()) {
        // --- JOYSTICKS (Range: -512 to 511) ---
        int lx = ctl->axisX();       // Left Stick X
        int ly = ctl->axisY();       // Left Stick Y
        int rx = ctl->axisRX();      // Right Stick X
        int ry = ctl->axisRY();      // Right Stick Y

        // --- TRIGGERS (Range: 0 to 1023) ---
        int lt = ctl->throttle();    // Left Trigger
        int rt = ctl->brake();       // Right Trigger

        // --- BUTTONS (Boolean) ---
        bool a = ctl->a();
        bool b = ctl->b();
        bool x = ctl->x();
        bool y = ctl->y();
        bool lb = ctl->l1();
        bool rb = ctl->r1();

        // --- DPAD (Bitmask) ---
        uint8_t dpad = ctl->dpad(); 

        // Output to Serial Monitor for debugging
        Serial.printf("STX: L(%4d,%4d) R(%4d,%4d) | TRG: L:%4d R:%4d | BTN: A:%d B:%d X:%d Y:%d LB:%d RB:%d | DPAD: %d\n",
                      lx, ly, rx, ry, lt, rt, a, b, x, y, lb, rb, dpad);
    }
    delay(10);
}
