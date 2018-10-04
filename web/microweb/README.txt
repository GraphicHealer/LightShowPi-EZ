Micro Web UI for LightShowPi

A very simple web page for controlling LightShowPi

To use : 

  On your Pi,

    Go to your base lightshowpi directory, typically /home/pi/lightshowpi
    > cd $SYNCHRONIZED_LIGHTS_HOME
    or 
    > cd /home/pi/lightshowpi

    Run the web server from the command line type
    > start_microweb

    If at any time you wish to stop Microweb, at the command line type
    > stop_microweb

  On your PC or mobile device,

    Open a browser to the following
    http://<PI>/
    where <PI> is the IP address of your Pi 


To run microweb at startup, the preferred method is:

> sudo crontab -e

Then add the following lines:

# set enviroment variable
# you might need to adjust the path if you did not install
# lightshowpi to the default directory
SYNCHRONIZED_LIGHTS_HOME=/home/pi/lightshowpi

@reboot $SYNCHRONIZED_LIGHTS_HOME/bin/start_microweb >> $SYNCHRONIZED_LIGHTS_HOME/logs/microweb.log 2>&1

* "Play Next" will only work for more than one song defined in playlist mode. 
All other modes will only restart the defined configuration.

* There are four pages available, main, playlist, tools, and configuration
  Main Page - Main controls for lights and starting the show. Volume control.
    - navigation to other pages by icon or button
  Playlist Page - Songs available in your defined playlist.
    - clicking a song will start it immediately
    - next song to be played is highlighted
  Tools Page - Shutdown/Reboot and individual channel operation
    - this page takes slightly longer to load
  Settings Page - View or Select your config file
    - create any config file in the format overrides*.cfg 
      in your config/ directory and it will be available to use.
      * can be any character or characters, but you must start with
      overrides and end with .cfg.
      microweb will use that file for all operations until changed.
    - edit .playlist files
      reorder files
      use selected files
    - upload music files to .playlist directory


Have fun.
Ken B
