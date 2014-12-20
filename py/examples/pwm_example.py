"""Example to show the use of the pwm functions in lightshowpi"""

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
    PWM example

    Start at each end and walk to the other using pwm
    """
    # required to cleanup all processes
    atexit.register(end, hc)

    # this is a list of all the channels you have access to
    lights = hc._GPIO_PINS

    # the gpio pins in reversed order
    lights2 = lights[::-1]

    # get _PWM_MAX from the hc module
    # this is the max value for the pwm channels
    pwm_max = hc._PWM_MAX

    # start with all the lights off
    hc.turn_off_lights()

    # pause for 1 second
    time.sleep(1)

    # working loop, we will do this sequence 10 times then end
    for _ in range(10):
        # here we just loop over the gpio pins and turn then on and off
        # with the pwm feature of lightshowpi
        for light in range(int(len(lights) / 2)):
            if hc.is_pin_pwm(lights[light]) and hc.is_pin_pwm(lights2[light]):
                for brightness in range(0, pwm_max):
                    # fade in
                    hc.turn_on_light(lights[light],
                                     0,
                                     float(brightness) / pwm_max)

                    hc.turn_on_light(lights2[light],
                                     0,
                                     float(brightness) / pwm_max)

                    time.sleep(.05 / pwm_max)

                for brightness in range(pwm_max - 1, -1, -1):
                    # fade out
                    hc.turn_on_light(lights[light],
                                     0,
                                     float(brightness) /pwm_max)

                    hc.turn_on_light(lights2[light],
                                     0,
                                     float(brightness) / pwm_max)

                    time.sleep(.05 / pwm_max)

        for light in range(int(len(lights) / 2)-1, -1, -1):
            if hc.is_pin_pwm(lights[light]) and hc.is_pin_pwm(lights2[light]):
                for brightness in range(0, pwm_max):
                    # fade in
                    hc.turn_on_light(lights[light],
                                     0,
                                     float(brightness) / pwm_max)

                    hc.turn_on_light(lights2[light],
                                     0,
                                     float(brightness) / pwm_max)

                    time.sleep(.05 / pwm_max)

                for brightness in range(pwm_max - 1, -1, -1):
                    # fade out
                    hc.turn_on_light(lights[light],
                                     0,
                                     float(brightness) / pwm_max)

                    hc.turn_on_light(lights2[light],
                                     0,
                                     float(brightness) / pwm_max)

                    time.sleep(.05 / pwm_max)

        # this is required so that an sms play now command will 
        # end your script and any subprocess you have statred
        if exit_event.is_set():
            break

if __name__ == "__main__":
    main()
