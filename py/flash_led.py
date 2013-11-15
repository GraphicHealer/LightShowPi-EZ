# Initial basic test app for turning on and off various GPIO ports

import time
import RPi.GPIO as GPIO
import argparse 

parser = argparse.ArgumentParser()
parser.add_argument('--led', type=int, default=0, help='led to flash (0-7)')
parser.add_argument('--sleep', type=float, default=.5, help='time to sleep between flash')
args = parser.parse_args()

leds = [11,12,13,15,16,18,22,7]
pin = leds[args.led]
sleep = args.sleep

GPIO.cleanup()
GPIO.setmode(GPIO.BOARD)
GPIO.setup(pin,GPIO.OUT)

while True:
	GPIO.output(pin,GPIO.HIGH)
	time.sleep(sleep)
	GPIO.output(pin,GPIO.LOW)
	time.sleep(sleep)

