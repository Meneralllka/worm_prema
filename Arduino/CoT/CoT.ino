void setup() {
  Serial.begin(9600); 
}

void loop() {
  // --- Current Sensor (ACS712) on A5 ---
  // Formula: (V_out - Offset) / Sensitivity
  // For a 20A module, sensitivity is typically 0.1V/A (100mV/A)
  float AcsValueF = ((analogRead(A5) * (5.0 / 1024.0)) - 2.5) / 0.1;

  // --- Voltage Sensor on A0 ---
  int voltageRaw = analogRead(A0);
  float vIn = voltageRaw * (5.0 / 1024.0);
  
  // If using a standard 25V voltage sensor module (which has a 5:1 divider):
  // The actual voltage is vIn / (R2/(R1+R2)), which simplifies to vIn * 5.0
  float actualVoltage = vIn * 5.0; 

  // --- Output ---
  Serial.print("Current: ");
  Serial.print(AcsValueF);
  Serial.print(" A | Voltage: ");
  Serial.print(actualVoltage);
  Serial.println(" V");

  delay(100); // Increased delay slightly for readability
}
