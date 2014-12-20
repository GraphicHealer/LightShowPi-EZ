"""Simple script to turn on all the lights"""

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
    """Turn all the lights on for 2 minutes"""
    # required to cleanup all processes
    atexit.register(end, hc)

    # turn on all the lights
    hc.turn_on_lights()

    # run for 2 minutes
    end = time.time() + 120

    # working loop will run as long as time.time() is less then "end"
    while time.time() < end:
        # this is required so that an sms play now command will 
        # end your script and any subprocess you have statred
        if exit_event.is_set():
            break

if __name__ == "__main__":
    main()
