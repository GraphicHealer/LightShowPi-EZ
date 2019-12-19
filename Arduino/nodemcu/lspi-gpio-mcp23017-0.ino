
/*
 * A sketch for NodeMCU devices to receive json udp data (truncated) when using :
 * [network]
 * networking = serverjson
 * 
 * Send all GPIO data to a MCP23017 device
 * 
 * Author: KenB
 * Version: 1.0
 * 
 * ToDo: 
 * Notes: When Serial.print(s) are enabled in loop(), GPIO states may not sync
 * Notes: Compatible with ArduinoJson 6 library
*/

#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include "Adafruit_MCP23017.h"

// Modify these lines :

const char* deviceName = "nodemcu-lspi"; //your preferred device name on your network
const char* ssid = "myssid";             //your wifi ssid
const char* password = "mypasswd";     //your wifi password

uint8_t mcp23017_address = 0x20;       //your mcp I2C address

int gpio_pins[] = {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15}; //all 16 available MCP23017 GPIOs

/* 
 *  channels[]
 *  must be the same number of elements as GPIOs the server is broadcasting ( typically 8 )
 *  negative numbers are ignored channels
 *  zero and up correspond to elements of the gpio_pins[] array above
*/
int channels[] = {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15}; // use all 16 channels when using MCP23017 GPIOs
//int channels[] = {-1,-2,-3,-4,0,1,2,3}; // ignore rcvd channels 1-4, use channels 5-8
//int channels[] = {0,1,2,3,-4,-5,-6,-7}; // ignore rcvd channels 5-8, use channels 1-4

// Rarely modify these lines :

#define BUFFER_SIZE 512 //increase the buffer size if your server gpios is really large
char incomingPacket[BUFFER_SIZE];  
unsigned int port = 8888;  //lspi standard

float turnon = 0.4; //threshold for ON ( onoff only supported here )

const short int BUILTIN_LED1 = 2; //GPIO2 on the NodeMCU

// uncomment these two for active_low_mode = no
int turn_on = HIGH;
int turn_off = LOW;
// uncomment these two for active_low_mode = yes
//int turn_on = LOW;
//int turn_off = HIGH; 


WiFiUDP udp;
Adafruit_MCP23017 mcp;

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

  mcp.begin(mcp23017_address);
  
  for (int i=0; i<(sizeof(gpio_pins)/sizeof(gpio_pins[0])); i++) {
    mcp.pinMode(gpio_pins[i], OUTPUT);
    Serial.printf("Set pinMode %d OUTPUT\n",gpio_pins[i]);
    mcp.digitalWrite(gpio_pins[i], turn_off);
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
    StaticJsonDocument<BUFFER_SIZE> jsonBuffer;
    deserializeJson(jsonBuffer,incomingPacket);
    JsonArray dataarray = jsonBuffer["data"];
    for (int i=0; i<dataarray.size() ; i++) {
      if (channels[i] < 0 ) {
        continue;
      }
      float pvf = dataarray.getElement(i).as<float>();
//      Serial.printf("array elem %d = %f\n", i, pvf);
      if (pvf >= turnon) {
//        Serial.printf("GPIO %d is ON\n", gpio_pins[channels[i]]);
        mcp.digitalWrite(gpio_pins[channels[i]], turn_on);
      } else if (pvf < 0.0) {
//        Serial.printf("GPIO %d is Unassigned\n", gpio_pins[channels[i]]);
        continue;
      } else {
//        Serial.printf("GPIO %d is OFF\n", gpio_pins[channels[i]]);
        mcp.digitalWrite(gpio_pins[channels[i]], turn_off);
      }   
         
    }   
//    digitalWrite(BUILTIN_LED1, LOW);
  }

}
