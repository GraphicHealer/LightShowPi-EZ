All files here are free for you to use as you wish.  All I ask in return is
that you send any updates / improvements you may make to them back to me so
that I can benefit from your improvements, and re-share them with others to
also benefit!

Join us on our Google+ community page as well to share your experiences
using lightshowPi, as well as videos of your shows!

https://plus.google.com/communities/101789596301454731630

Thanks, and enjoy ;)

Todd Giles ([todd.giles@gmail.com](mailto:todd.giles@gmail.com))

Projects:
=========

Synchronized Lights
-------------------

* py/synchronized_lights.py - Play a single song while synchronizing lights to the music.
* py/hardware_controller.py - Useful for verifying your hardware configuration (blink all lights, turn them on / off, etc...).
* py/check_sms.py - Check sms messages from a google voice account to allow for voting for the next song!
* config/* - Configuration files go here.
* crontab/synchronized_lights - Add these via 'sudo crontab -e' to start / stop the lightshow automatically
* logs/* - Log files go here.
* bin/* - Various bash scripts / tools to aid in playing songs, controlling volume, etc...

Setup
-----

* Setup the environment
	- Create an enviroment variable to specify the programs home directory. Edit `/etc/environment` and add the following line to the file replacing `/path/to/yourdirectory` with the location where you placed the program files
		- `SYNCHRONIZED_LIGHTS_HOME=/path/to/yourdirectory`
	- Modify `/etc/sudoers` file to allow the `SYNCHRONIZED_LIGHTS_HOME` variable to be preserved when using sudo. Add the following line to the file:
		- `Defaults	env_keep += "SYNCHRONIZED_LIGHTS_HOME"`
* Modify the configuration files to fit your system.  The configuration files are located in the `config` directory.
	- TODO(toddgiles): Add step-by-step instructions to what configurations MUST be modified to get things working in a new setup.
