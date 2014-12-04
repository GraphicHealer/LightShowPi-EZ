 
This is a little guide to help you write your own little python scripts to
control a custom aftershow

It will require you to learn a little bit of python
https://www.python.org/

But don't worry is not all that hard and with just a few commands you can 
make your lights do all kinds of things.

Lets start with a basic templet that you will need to follow

[code]
import time
import hardware_controller as hc

lights = hc._GPIO_PINS

def main():
    hc.initialize()
    
    while True:
        
        <your code here>
            
    hc.clean_up(True)
[/code]

First import your modules.

The time module is not strictly needed but it comes in handy

The hardware_controller module is needed do don't forget to import it

I think it's a good idea to assign the list of gpio pins to an easy to
remember, but _GPIO_PINS in hardware_controller is the same list, you 
can decide which way you want to use them.

You need to place your code in the main() function inside a loop of some kind

After your loop finishes you need to shut everything down by calling
hc.clean_up(True)


The functions that you will need to use from the hardware_controller module

initialize()
    initialize the hardware 
    hc.initialize()
    
clean_up()
    used to shut everything down, you will need to pass in True for this to work
    hc.clean_up()
    
turn_on_light()
    this will turn on one light, you need to pass in the the gpio pin number
    if your gpio pins are set to onoff instead of pwm and you have allways_on
    allways_off channels set in your config files you can add an argument to 
    enforce these settings
    hc.turn_on_light(pin#, useoverrides=0)
    
turn_off_light()
    the oppisite of turn_on_light()
    hc.turn_off_light(pin#, useoverrides=0)
    
turn_on_lights()
    this will turn on all the light  if your gpio pins are set to onoff instead 
    of pwm and you have allways_on allways_off channels set in your config files
    you can add an argument to enforce these settings
    turn_on_lights(usealwaysonoff=0)
    
turn_off_lights()
    the oppisite of turn_off_lights()
    turn_off_lights(usealwaysonoff=0)
    
you can use any combonaion of the above to create anything you wish

included are several basic examples to get you started

Happy coding
    
    
    
    
    
    