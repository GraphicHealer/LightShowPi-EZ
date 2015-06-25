"""Example Template"""

# This import gives you full acess to the hardware
import hardware_controller as hc

lights = hc._GPIO_PINS

def main():
    """
    Empyt script template for you to use
    """
    # initialize our hardware for use
    hc.initialize()

    # USE ONE OF THE BELOW LOOPS AS A STARTING POINT
    # JUST UNCOMMENT ONE AND DELETE THE OTHERS

    #for count in range(10):

    #count = 0
    #while count < 10:
        #count += 1

    # change number_of_seconds_to_run_for to the number of seconds you what
    # this to run for 60 is 1 minute 3600 is 1 hour

    #end_time = time.time() + number_of_seconds_to_run_for
    #while time.time() < end_time:

    ####<PUT ALL YOU CODE IN THIS BLOCK>

    # clean up and end
    hc.clean_up()

if __name__ == "__main__":
    main()
