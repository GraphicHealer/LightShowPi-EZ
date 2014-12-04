import time

# This import gives you full acess to the hardware
import hardware_controller as hc

# this is a list of all the channels you have access to
lights = hc._GPIO_PINS

def main():
    """
    latter
    
    Lights one channel at a time in order
    Then backs down to the first
    """
    # initialize your hardware for use
    hc.initialize()
    
    print "Press <CTRL>-C to stop"

    # lets make sure we start with all the lights off
    hc.turn_off_lights()
    
    # pause for 1 second
    time.sleep(1)

    # working loop
    while True:
        # try except block to catch the <CTRL>-C to stop
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

            # to make the transition back smoother handle the last one here
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

            # angain to make it smoother handle the 
            # first light like the last light
            hc.turn_off_lights()
            hc.turn_on_light(lights[light - 1])
                
        except KeyboardInterrupt:
            print "\nstopped"
            
            # This ends and cleans up everything 
            # NOTE: if you do not pass in True
            #       this will start all over again
            #       and you will have to fight to
            #       get out of the loop
            hc.clean_up(True)
            break

if __name__ == "__main__":
    main()
