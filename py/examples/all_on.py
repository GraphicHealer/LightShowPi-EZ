"""Simple script to turn on all the lights"""

import time

# This import gives you full acess to the hardware
import hardware_controller as hc

def main():
    """Turn all the lights on for 2 minutes"""

    # initialize your hardware for use
    hc.initialize()

    # turn on all the lights
    hc.turn_on_lights()

    # run for 2 minutes
    end = time.time() + 120

    # working loop will run as long as time.time() is less then "end"
    while time.time() < end:
        # try except block to catch keyboardinterrupt by user to stop
        try:
            # do nothing, just wait
            pass
        # if the user pressed <CTRL> + C to exit early break out of the loop
        except KeyboardInterrupt:
            print "\nstopped"
            break

    # This ends and cleans up everything
    hc.clean_up()

if __name__ == "__main__":
    main()
