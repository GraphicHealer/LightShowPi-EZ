 
This is a little guide to help you write your own little python scripts to
control a custom pre or post show

It will require you to learn a little bit of python
https://www.python.org/

But don't worry is not all that hard and with just a few commands you can 
make your lights do all kinds of things.

Lets start with a basic template that you will need to follow

[code]

import atexit
import time

def end(hc):
    hc.turn_off_lights()

def main(hc, exit_event):
    atexit.register(end, hc)

    lights = hc._GPIO_PINS
    
    <a loop>
    
        <your code here>
            
        if exit_event.is_set():
            break

if __name__ == "__main__":
    main()

[/code]

First import your modules.

The atexit module is need, it's a handy way for us to make sure that
every thing that we need to do at the end of the script happens
even if we press <CTRL>+C it will still do everything we need done to
make the script end cleanly, like turn the lights off, or kill a subprocess

The time module is not strictly needed but it comes in handy

def end(hc):
    hc.turn_off_lights()

The above code is use to clean up everything after your script ends.  Anything 
you want to happen as the script ends you do here.  With the use of the atexit module
it will be done no matter what, even if an error happens this function will still be called.
So don't forget to include it.

You need to place most of your code in the main() function inside a loop of some kind.

For the pre or post show to call your main function you need to include some parameters
in the function definition.  hc and exit_event making your definition look like the below example

def main(hc, exit_event):

hc is the hardware controller and it is need if you want to do anything with your lights
and exit_event is used to end your script if a play now request comes in.
Both must be included or your script will not work

atexit.register(end, hc)
The above line needs to be in you main function, either as the first line or
just before the working loop, this line tells the script what to do when it ends.
So if you want everything to work right after you script finishes make sure to include it before the loop.

Then I think it's a good idea to assign the list of gpio pins to an easy to remember
variable name, but _GPIO_PINS in hardware_controller is the same list,
you can decide which way you want to use them.
You can also setup other things at this point if you need or want to.
Setup other variables (like storing a start time from the time module)
Start playing some audio.
What ever you might need.

The loop is where almost everything will happen
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

This is used by the pre/post shows to exit your script if a play now request happens
include this in the working loop, either at the top or bottom, it dosen't matter,
as long as it is in there.
if exit_event.is_set():
    break
            
After your loop finishes it will automaticaly clean up after it self as long as
you included the end() function and atexit.register.


These are the functions that you can use from the hardware_controller module

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
