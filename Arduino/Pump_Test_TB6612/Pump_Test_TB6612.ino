#define AIN1 19 // Motor A Input 1
#define AIN2 18 // Motor A Input 2
#define PWMA 5 // Motor A PWM

void setup() {
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(PWMA, OUTPUT);
}

void loop() {
  // put your main code here, to run repeatedly:
  digitalWrite(AIN1, 1);
  digitalWrite(AIN2, 0);
  analogWrite(PWMA, 255);
  delay(10000);
  digitalWrite(AIN1, 0);
  digitalWrite(AIN2, 1);
  analogWrite(PWMA, 255);
  delay(10000);
}
