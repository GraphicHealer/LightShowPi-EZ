
/*
 * A sketch for NodeMCU devices to receive json udp data (truncated) when using :
 * [network]
 * networking = serverjson
 * 
 * Author: KenB
 * Version: 1.2 ( experimental )
 * 
 * ToDo: 
 * 
 * Notes: When Serial.print(s) are enabled in loop(), GPIO states may not sync 
 */

#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

// Modify these lines :

const char* deviceName = "nodemcu-lspi"; // your preferred device name on your network
const char* ssid = "myssid";             // your wifi ssid
const char* password = "mypasswd";       // your wifi password

/*
 *  gpio_pins[]
 *  an array of the NodeMCU GPIO pins you want to use
 */
//int gpio_pins[] = {4,5,12,13,14,15,0,3}; // all 8 available NodeMCU GPIOs, others may give you trouble
int gpio_pins[] = {4,5,13,14};             // four basic GPIOs

/* 
 *  channels[]
 *  must be the same number of elements as GPIOs the server is broadcasting ( typically 8 )
 *  negative numbers are ignored channels
 *  zero and up correspond to elements of the gpio_pins[] array above
 */
//int channels[] = {0,1,2,3,4,5,6,7};     // use all 8 channels when using 8 GPIOs
//int channels[] = {-1,-2,-3,-4,0,1,2,3}; // ignore rcvd channels 1-4, use channels 5-8
int channels[] = {0,1,2,3,-4,-5,-6,-7};   // ignore rcvd channels 5-8, use channels 1-4

// Rarely modify these lines :

char incomingPacket[512];  // increase the buffer size if your server gpios is really large
unsigned int port = 8888;  // lspi standard

float turnon = 0.4; // threshold for ON ( onoff only supported here )

const short int BUILTIN_LED1 = 2; // GPIO2 on the NodeMCU

WiFiUDP udp;

void setup() {
  Serial.begin(115200);
  delay(10);

  Serial.println("WiFi Startup");

  WiFi.hostname(deviceName);
  WiFi.begin(ssid, password);
  WiFi.mode(WIFI_STA);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  pinMode(BUILTIN_LED1, OUTPUT);
  digitalWrite(BUILTIN_LED1, LOW);
  Serial.println("\nConnected");

  for (int i=0; i<(sizeof(gpio_pins)/sizeof(gpio_pins[0])); i++) {
    pinMode(gpio_pins[i], OUTPUT);
    Serial.printf("Set pinMode %d OUTPUT\n",gpio_pins[i]);
    digitalWrite(gpio_pins[i], LOW);
  }

  udp.begin(port);

}

void loop() {

  int packetSize = udp.parsePacket();
  if (packetSize) {
//    digitalWrite(BUILTIN_LED1, HIGH);
//    Serial.printf("Received %d bytes from %s, port %d\n", packetSize, udp.remoteIP().toString().c_str(), udp.remotePort());
    int len = udp.read(incomingPacket, sizeof(incomingPacket));
    if (len > 0)
    {
      incomingPacket[len] = 0; 
    }
//    Serial.printf("UDP packet contents: %s\n", incomingPacket);
    StaticJsonBuffer<512> jsonBuffer;
    JsonObject& jsonobject = jsonBuffer.parseObject(incomingPacket);
    JsonArray& dataarray = jsonobject["data"];
    for (int i=0; i<dataarray.size() ; i++) {
      if (channels[i] < 0 ) {
        continue;
      } 
      float pvf = String(dataarray.get<char*>(i)).toFloat();
//      Serial.printf("array elem %d = %f\n", i, pvf);
      if (pvf >= turnon) {
//        Serial.printf("GPIO %d is ON\n", gpio_pins[channels[i]]);
        digitalWrite(gpio_pins[channels[i]], HIGH);
      } else {
//        Serial.printf("GPIO %d is OFF\n", gpio_pins[channels[i]]);
        digitalWrite(gpio_pins[channels[i]], LOW);
      }   
         
    }   
//    digitalWrite(BUILTIN_LED1, LOW);
  }

}

