/*
 * A sketch for NodeMCU devices to receive raw udp data (truncated) when using :
 * [network]
 * networking = serverraw
 * 
 * Author: KenB
 * Version: 1.0 ( experimental )
 * 
 * ToDo: Make parsing code more robust for damaged packets
*/

#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

// Modify these lines :

const char* deviceName = "nodemcu-lspi"; //your preferred device name on your network
const char* ssid = "myssid";             //your wifi ssid
const char* password = "mypassword";     //your wifi password

int gpio_pins[] = {4,5,13,14};           //these are NodeMCU GPIO pins you want to use
/* 
 *  channels[]
 *  must be the same number of elements as GPIOs the server is broadcasting ( typically 8 )
 *  negative numbers are ignored channels
 *  zero and up correspond to elements of the gpio_pins[] array above
*/ 
//int channels[] = {-1,-2,-3,-4,0,1,2,3}; // ignore rcvd channels 1-4, use channels 5-8
int channels[] = {0,1,2,3,-4,-5,-6,-7}; // ignore rcvd channels 5-8, use channels 1-4

// Rarely modify these lines :

char incomingPacket[512];  //increase the buffer size if your server gpios is really large
unsigned int port = 8888;  //lspi standard

float turnon = 0.4; //threshold for ON ( onoff only supported here )

const short int BUILTIN_LED1 = 2; //GPIO2 on the NodeMCU

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
  Serial.println("Connected");

  for (int i=0; i<(sizeof(gpio_pins)/sizeof(gpio_pins[0])) -1 ; i++) {
    pinMode(gpio_pins[i], OUTPUT);
    Serial.printf("Set pinMode %d OUTPUT",gpio_pins[i]);
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
    char *p;
    char *parsevalue = strtok_r(incomingPacket, " ", &p);
    int channelcount = 0;
    while (parsevalue != NULL) {
      if (channels[channelcount] >= 0 ) {

        float pvf = String(parsevalue).toFloat();
        if (pvf >= turnon) {
//          Serial.printf("GPIO %d is ON\n", gpio_pins[channels[channelcount]]);
          digitalWrite(gpio_pins[channels[channelcount]], HIGH);
        } else {
//          Serial.printf("GPIO %d is OFF\n", gpio_pins[channels[channelcount]]);
          digitalWrite(gpio_pins[channels[channelcount]], LOW);
        }

      }
      if (channelcount >= ( (sizeof(channels)/sizeof(channels[0])) -1 )) {
        break;
      }
      parsevalue = strtok_r(NULL, " ", &p);
      channelcount += 1;
    }
    
//    digitalWrite(BUILTIN_LED1, LOW);
  }

}
