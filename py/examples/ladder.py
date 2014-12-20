"""Simple script to walk the lights up and down"""

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
    ladder

    Lights one channel at a time in order
    Then backs down to the first
    Then repeat everything 20 times
    """
    # required to cleanup all processes
    atexit.register(end, hc)

    # this is a list of all the channels you have access to
    lights = hc._GPIO_PINS

    # start with all the lights off
    hc.turn_off_lights()

    # pause for 1 second
    time.sleep(1)

    # working loop
    for _ in range(20):
        # here we just loop over the gpio pins and do something with them
        # except the last one
        for light in range(len(lights)-1):
            # turn off all the lights
            hc.turn_off_lights()

            # then turn on one
            hc.turn_on_light(lights[light])

            # wait a little bit
            time.sleep(.04)

        # to make the transition back smoother we handle the last pin here
        hc.turn_off_lights()
        hc.turn_on_light(lights[light + 1])

        # this loop walks it back the other way
        for light in range(len(lights)-1, 0, -1):
            # turn off all the lights
            hc.turn_off_lights()

            # then turn on one
            hc.turn_on_light(lights[light])

            # wait a little bit
            time.sleep(.04)

        # again to make it smoother handle the first pin like the last pin
        hc.turn_off_lights()
        hc.turn_on_light(lights[light - 1])

        # this is required so that an sms play now command will 
        # end your script and any subprocess you have statred
        if exit_event.is_set():
            break

if __name__ == "__main__":
    main()
