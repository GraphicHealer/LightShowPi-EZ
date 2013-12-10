All files here are free for you to use as you wish.  All I ask in return is
that you send any updates / improvements you may make to them back to me so
that I can benefit from your improvements, and re-share them with others to
also benefit!

Thanks, and enjoy ;)

Todd Giles ([todd.giles@gmail.com](mailto:todd.giles@gmail.com))

Projects:
=========

Synchronized Lights
-------------------

* py/synchronized_lights.py - Play a single song while synchronizing lights to the music.
* py/check_sms.py - Check sms messages from a google voice account to allow for voting for the next song!
* crontab/synchronized_lights - Add these via 'sudo crontab -e' to start / stop the lightshow automatically
* bin/* - Various bash scripts to aid in playing songs, controlling volume, etc...  Copy them all into your /home/pi/bin/ directory, and ensure you add /home/pi/bin/ to your PATH

Setup
-----

* Setup the environment
	-Create an enviroment variable to specify the programs home directory. Edit /etc/environment and add the following to line to the file replacing /path/yourdirectory with the location where you placed the program files
		- $SYNCHRONIZED_LIGHTS_HOME=/path/yourdirectory

	- Modify /etc/sudoers file to allow the SYNCHRONIZED_LIGHTS_HOME variable to be preserved when using sudo. Add the following line to the file.
		- Defaults	env_keep += "SYNCHRONIZED_LIGHTS_HOME"
