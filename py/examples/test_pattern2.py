"""Turn off one light at a time with the others in an on state"""

import time

# This import gives you full acess to the hardware
import hardware_controller as hc

def main():
    """
    Test pattern2

    Unlights one channel at a time in order
    """
    # this is a list of all the channels you have access to
    lights = hc._GPIO_PINS

    # initialize your hardware for use
    hc.initialize()

    # start with all the lights off
    hc.turn_off_lights()

    # pause for 1 second
    time.sleep(2)

    # working loop
    for _ in range(50):
        # try except block to catch keyboardinterrupt by user to stop
        try:
            # here we just loop over the gpio pins and do something with them
            for light in lights:
                # turn on all the lights
                hc.turn_on_lights()

                # then turn off one
                hc.turn_off_light(light)

                # wait a little bit before the for loop
                # starts again and turns off the next light
                time.sleep(.4)

        # if the user pressed <CTRL> + C to exit early break out of the loop
        except KeyboardInterrupt:
            print "\nstopped"
            break

    # This ends and cleans up everything
    hc.clean_up()

if __name__ == "__main__":
    main()
