#include <WiFi.h>
#include <Firebase_ESP_Client.h>

// Provide the token generation process info & RTDB helper functions
#include <addons/TokenHelper.h>
#include <addons/RTDBHelper.h>

// --- 1. Hotspot Wi-Fi Credentials ---
const char* ssid = "Galaxy S24 Ultra D870"; 
const char* password = "12345678"; 

// --- 2. Firebase Credentials ---
// Remove "https://" and trailing "/"
#define DATABASE_URL "mass-shifter-default-rtdb.firebaseio.com" 
#define DATABASE_SECRET "LAnPBF4rxcT9tb8p8nmC9R6INrWN12RVw5NdSsnM" 

// Firebase Objects & Timers
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

unsigned long lastFirebaseCheck = 0;
// Polling every 500ms so it's readable in the Serial Monitor
const int fetchInterval = 500; 

void setup() {
    Serial.begin(115200);
    delay(1000);

    // --- Connect to Wi-Fi ---
    Serial.print("\nConnecting to Hotspot: ");
    Serial.println(ssid);
    
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    
    Serial.println("\nWi-Fi Connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    // --- Connect to Firebase ---
    Serial.println("Connecting to Firebase...");
    config.database_url = DATABASE_URL;
    config.signer.tokens.legacy_token = DATABASE_SECRET;
    
    Firebase.begin(&config, &auth);
    Firebase.reconnectWiFi(true);
    
    Serial.println("Firebase Ready! Waiting for data...\n");
}

void loop() {
    // Non-blocking fetch
    if (Firebase.ready() && (millis() - lastFirebaseCheck > fetchInterval)) {
        lastFirebaseCheck = millis();

        // 1. Fetch Amplitude
        if (Firebase.RTDB.getFloat(&fbdo, "/robot_params/amplitude")) {
            Serial.print("Amplitude: ");
            Serial.print(fbdo.to<float>());
        } else {
            Serial.print("Amp Error: ");
            Serial.print(fbdo.errorReason());
        }

        // 2. Fetch Lag
        if (Firebase.RTDB.getFloat(&fbdo, "/robot_params/lag")) {
            Serial.print(" | Lag: ");
            Serial.print(fbdo.to<float>());
        }

        // 3. Fetch Power
        if (Firebase.RTDB.getFloat(&fbdo, "/robot_params/power")) {
            Serial.print(" | Power: ");
            Serial.println(fbdo.to<float>());
        }
    }
}
