#include <Servo.h>

Servo servos[4]; // Using an array makes the code much cleaner
int pins[] = {2, 3, 4, 5};
float phase = 0; // Tracks the movement of the wave

void setup() {
  for(int i = 0; i < 4; i++) {
    servos[i].attach(pins[i]);
  }
}

void loop() {
  // Movement Parameters
  float amplitude = 40;   // How wide the snake curves (0-90)
  float frequency = 5;    // How fast it moves
  float lag = 0.8;        // The "Phase Shift" - this creates the wave

  for(int i = 0; i < 4; i++) {
    // Calculate the angle for each servo using a Sine wave
    // Formula: Center(90) + sin(Time + Offset per segment) * Width
    float angle = 90 + sin(phase + (i * lag)) * amplitude;
    servos[i].write(angle);
  }

  phase += 0.2; // Increase this to speed up the wave
  delay(20);    // Small delay for smooth motion
}
