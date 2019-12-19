import os
import sys
import argparse
import time
import bibliopixel.colors as colors

HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
sys.path.insert(0, HOME_DIR + '/py')
import led_module
import configuration_manager

cm = configuration_manager.Configuration()

parser = argparse.ArgumentParser()

parser.add_argument('--config', default="",
                   help='LED Config File')

parser.add_argument('--sleep', default="0.1",
                   help='LED sleep interval')

args = parser.parse_args()

cm.set_led(config_file=args.config)

led = led_module.Led(cm.led,serpentine=True,vert_flip=True,rotation=90)

if cm.led.led_configuration == "MATRIX":
    try:
        for x in range(0,cm.led.matrix_width):
            for y in range(0,cm.led.matrix_height):
                print("LED on = " + str(x) + "," + str(y))
                led.led.set(x,y,colors.White)
                led.led.push_to_driver()
                time.sleep(float(args.sleep))
                led.all_leds_off()
        led.led.push_to_driver()
    except KeyboardInterrupt:
        led.exit_function()

else:
    try:
        for i in range(0,led.led_count):
            print("LED on = " + str(i))
            led.led.set(i,colors.White)
            led.led.push_to_driver()
            time.sleep(float(args.sleep))
            led.all_leds_off()
        led.led.push_to_driver()
    except KeyboardInterrupt:
        led.exit_function()
