"""Simply script to walk the lights up and down"""

import time

# This import gives you full acess to the hardware
import hardware_controller as hc

def main():
    """
    ladder

    Lights one channel at a time in order
    Then backs down to the first
    Then repeat everything 20 times
    """
    # this is a list of all the channels you have access to
    lights = hc._GPIO_PINS

    # initialize your hardware for use
    hc.initialize()

    # start with all the lights off
    hc.turn_off_lights()

    # pause for 1 second
    time.sleep(1)

    # working loop
    for _ in range(20):
        # try except block to catch keyboardinterrupt by user to stop
        try:
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

        # if the user pressed <CTRL> + C to exit early break out of the loop
        except KeyboardInterrupt:
            print "\nstopped"
            break

    # This ends and cleans up everything
    hc.clean_up()

if __name__ == "__main__":
    main()
