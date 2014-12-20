"""Example Template"""

# this module is needed so that we may exit this script 
# and clean up after out script ends
import atexit

# this is where we do the cleanup and end everything.
# if you start any subprocess you will need to pass in
# a reference to that subprocess, (view play_message.py for an example)
def end(hc):
    hc.turn_off_lights()

lights = hc._GPIO_PINS

# hc and exit_event are passed in the pre/post show script so that you
# have access to the hardware controller, and an exit_event generated
# by the pre/post show script. Do not forget to include then as if you
# do not your script will not work
def main(hc, exit_event):
    """
    Empyt script template for you to use
    """
    # required to cleanup all processes
    atexit.register(end, hc)

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
        
        # include this in your loop
        # it is required so that an sms play now command will 
        # end your script and any subprocess you have statred
        if exit_event.is_set():
            break

if __name__ == "__main__":
    main()
