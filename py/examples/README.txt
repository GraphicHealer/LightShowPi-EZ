 
This is a little guide to help you write your own little python scripts to
control a custom pre or post show

It will require you to learn a little bit of python
https://www.python.org/

But don't worry is not all that hard and with just a few commands you can 
make your lights do all kinds of things.

Lets start with a basic template that you will need to follow

[code]
import time
import hardware_controller as hc

lights = hc._GPIO_PINS

def main():
    hc.initialize()
    
    <a loop>
    
        <your code here>
            
    hc.clean_up()

if __name__ == "__main__":
    main()

[/code]

First import your modules.

The time module is not strictly needed but it comes in handy

The hardware_controller module is needed do don't forget to import it

I think it's a good idea to assign the list of gpio pins to an easy to remember
variable name, but _GPIO_PINS in hardware_controller is the same list,
you can decide which way you want to use them.

You need to place your code in the main() function inside a loop of some kind

while <exit condition>:
or
for count in range(<number>):

A for loop will execute the body of the loop a set number of times

>>> for count in range(10):
...     print count
... 
0
1
2
3
4
5
6
7
8
9

The above for loop will run through 10 times and print the value of count each time
From 0 to 9, python starts counting at 0

A while loop will execute the body of the loop until the <exit condition> is met

>>> count = 0
>>> while count < 10:
...     print count
...     count = count + 1
... 
0
1
2
3
4
5
6
7
8
9

The above while loop will run through as long as count is less then 10
This time we started with count = 0 and told it to stop when count was greater then 9
if you print the value of count you will see that it equals 10
>>> print count
10

In your loop you added 1 to count every time through after you printed the result
After 9 was printed you added 1 to count making it 10, but the next time through
the loop count as not less then 10 (it was 10) so the loop exited 

Either is fine, just remember to test your <exit condition> if you use a while loop
a bad <exit condition> will cause the loop not to run or trap you in an infinite loop

After your loop finishes you need to shut everything down by calling
hc.clean_up(True)

The main() function must be started for it to do anything, making the following
a must.

if __name__ == "__main__":
    main()


These are the functions that you can use from the hardware_controller module

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

You can use any combination of the above to create anything you wish

Included are several basic examples to get you started
Please look at the examples as they will show you better how to use the above 
functions, and show you some other things that you might want to do.
Two examples of note are play_message.py and PWM_example, the first has an example
that allows you to play an audio file while you are manipulating the lights
the latter is an examples of using the software PWM feature offered in lightshowpi.

Happy coding
