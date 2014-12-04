import time

# This import gives you full acess to the hardware
import hardware_controller as hc

# this is a list of all the channels you have access to
lights = hc._GPIO_PINS

def main():
    """
    Test pattern 1 
    
    Lights one channel at a time in order
    """
    # initialize your hardware for use
    hc.initialize()
    
    print "Press <CTRL>-C to stop"

    # trun on all the lights
    hc.turn_on_lights()
    
    # working loop
    while True:
        # try except block to catch the <CTRL>-C to stop
        try:
            # we are doing is waiting for <CTRL>-C to quit
            pass
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
