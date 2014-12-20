"""Turn off one light at a time with the others in an on state"""

import time

# this module is needed so that we may exit this script 
# and clean up after out script ends
import atexit

# this is where we do the cleanup and end everything.
def end(hc):
    hc.turn_off_lights()

# hc and exit_event are passed in the pre/post show script so that you
# have access to the hardware controller, and an exit_event generated
# by the pre/post show script. Do not forget to include then as if you
# do not your script will not work
def main(hc, exit_event):
    """
    Test pattern2

    Unlights one channel at a time in order
    """
    # required to cleanup all processes
    atexit.register(end, hc)

    # this is a list of all the channels you have access to
    lights = hc._GPIO_PINS

    # start with all the lights off
    hc.turn_off_lights()

    # pause for 1 second
    time.sleep(2)

    # working loop
    for _ in range(50):
        # here we just loop over the gpio pins and do something with them
        for light in lights:
            # turn on all the lights
            hc.turn_on_lights()

            # then turn off one
            hc.turn_off_light(light)

            # wait a little bit before the for loop
            # starts again and turns off the next light
            time.sleep(.4)

        # this is required so that an sms play now command will 
        # end your script and any subprocess you have statred
        if exit_event.is_set():
            break

if __name__ == "__main__":
    main()
