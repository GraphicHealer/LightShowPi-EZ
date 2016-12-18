#include <EEPROM.h>

// define pins use with your arduino

// ONEWIREPIN is for use with led strips that do not have a clock line
// just a data line.
#define ONEWIREPIN 2

// Data and Clock pins
// if you use the ICSP header you do not need to set these values.
// If you need/want to you can set them to something else here.
// Arduino Nano, Pro, Pro Mini, Micro, Uno, Duemilanove
//#define SPI_DATA 11
//#define SPI_CLOCK 13
//arduino Mega
//#define SPI_DATA 51
//#define SPI_CLOCK 52

// pin 15 is A0 on an Uno, on the Mega it is RX3.
// you can change this to any free pin that you have
#define rebootPin 15

#define FREE_RAM_BUFFER 180

#define GENERIC 0
#define LPD8806 1
#define WS2801 2
#define NEOPIXEL 3       //NEOPIXEL also known as WS2811, WS2812, WS2812B, APA104
#define WS2811_400 4     //400khz variant of above
#define TM1809_TM1804 5
#define TM1803 6
#define UCS1903 7
#define SM16716 8
#define APA102 9
#define LPD1886 10 
#define P9813 11 

#define CONFIGCHECK 7
#define EMPTYMAX 100

template <class T> int EEPROM_writeAnything(int ee, const T& value){
    const byte* p = (const byte*)(const void*)&value;
    unsigned int i;
    for (i = 0; i < sizeof(value); i++)
        EEPROM.write(ee++, *p++);
    return i;
}

template <class T> int EEPROM_readAnything(int ee, T& value){
    byte* p = (byte*)(void*)&value;
    unsigned int i;
    for (i = 0; i < sizeof(value); i++)
        *p++ = EEPROM.read(ee++);
    return i;
}


inline void doReboot(){
    digitalWrite(rebootPin, LOW);
    while (1);
}

namespace CMDTYPE
{
    enum CMDTYPE
    {
        SETUP_DATA = 1,
        PIXEL_DATA = 2,
        BRIGHTNESS = 3,
        GETID      = 4,
        SETID      = 5,
    };
}

namespace RETURN_CODES
{
    enum RETURN_CODES
    {
        SUCCESS = 255,
        REBOOT = 42,
        ERROR = 0,
        ERROR_SIZE = 1,
        ERROR_UNSUPPORTED = 2,
        ERROR_PIXEL_COUNT = 3,
    };
}

struct config_t{
    uint8_t type;
    uint16_t pixelCount;
    uint8_t spiSpeed;
} config;

void writeConfig(){
    EEPROM_writeAnything(1, config);
}

void readConfig(){
    EEPROM_readAnything(1, config);
}

void writeDefaultConfig(){
    config.type = LPD8806;
    config.pixelCount = 1;
    config.spiSpeed = 16;
    writeConfig();
    EEPROM.write(16, 0);
}

uint32_t freeRam(){
    extern int __heap_start, *__brkval;
    int v;
    return (int)&v - (__brkval == 0 ? (int)&__heap_start : (int)__brkval);
}
