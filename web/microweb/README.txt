Micro Web UI for LightShowPi

A very simple web page for controlling LightShowPi

To use : 

On your Pi,

1) Go to your base lightshowpi directory, typically /home/pi/lightshowpi
> cd $SYNCHRONIZED_LIGHTS_HOME
or 
> cd /home/pi/lightshowpi

2) Run the web server from the command line type
> start_microweb

On your PC or mobile device,

3) Open a browser to the following
http://<PI>/
where <PI> is the IP address of your Pi 


Very simple operation, but note that "Play Next" will only work for more
than one song defined in playlist mode. All other modes will only restart
the defined configuration.

If at any time you wish to stop Microweb, at the command line type
> stop_microweb


Have fun.
Ken B
