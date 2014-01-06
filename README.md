All files here are free to use under the BSD License (see the LICENSE file for details).  All we
ask in return is that you send any updates / improvements you may make to them back to us so 
that we can all benefit from your improvements!

Join us on our [Google+ community page](https://plus.google.com/communities/101789596301454731630)
as well to share your experiences using lightshowPi, as well as videos of your shows!

Thanks, and enjoy ;)

Todd Giles ([todd.giles@gmail.com](mailto:todd.giles@gmail.com))

Installation / Getting Started
===========================

Please visit the [Wiki](https://bitbucket.org/togiles/lightshowpi/wiki/Home) for details on getting
started.  Or for those who want to just jump on in, feel free to run the install.sh script and go 
for it :-)

Directory Structure:
==================

* py/synchronized_lights.py - Play a single song while synchronizing lights to the music.
* py/hardware_controller.py - Useful for verifying your hardware configuration (blink all lights, turn them on / off, etc...).
* py/check_sms.py - Check sms messages from a google voice account to allow for voting for the next song!
* config/* - Configuration files go here.
* crontab/synchronized_lights - Add these via 'sudo crontab -e' to start / stop the lightshow automatically
* logs/* - Log files will be output here.
* bin/* - Various bash scripts / tools to aid in playing songs, controlling volume, etc...
<<<<<<< HEAD

Setup / Install
-------------

These instructions assume you already have a working [raspberryPi](http://www.raspberrypi.org/) installed with a recent
version of [raspbian](http://www.raspbian.org/).  It also does not cover hardware configuration at all, other than we
use [wiringPi](http://wiringpi.com/) to control turning lights on and off.

* Download the latest version of the repository using git:
    - `git clone https://togiles@bitbucket.org/togiles/lightshowpi.git`	
* Modify the configuration files to fit your system.  The configuration files are located in the `config` directory:
	- TODO(toddgiles): Add step-by-step instructions to what configurations MUST be modified to get things working in a new setup.
* Run the install script to retrieve the various dependencies lightshowPi uses:
    - `cd /home/pi/lightshow` (or to whatever directory you downloaded the repository to)
	- `sudo ./install.sh`
* For SMS use, create a google voice account and run `gvoice` to generate a default ~/.gvoice file, then modify the file to ensure your email and password are included
=======
>>>>>>> f636b6af59fd9133afd977147135fca043d7c4ff
