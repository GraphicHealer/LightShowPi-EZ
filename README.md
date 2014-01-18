http://www.lightshowpi.com/

All files here are free to use under the BSD License (see the LICENSE file for details).  All we
ask in return is that you send any updates / improvements you may make to them back to us so 
that we can all benefit from your improvements!

Join us on our [Google+ community page](https://plus.google.com/communities/101789596301454731630)
as well to share your experiences using lightshowPi, as well as videos of your shows!

Thanks, and enjoy ;)

Todd Giles ([todd.giles@gmail.com](mailto:todd.giles@gmail.com))

Installation / Getting Started
==============================

Please visit the [Wiki](https://bitbucket.org/togiles/lightshowpi/wiki/Home) for details on getting
started.  Or for those who want to just jump on in, feel free to run the install.sh script and go 
for it :-)

Directory Structure
===================

* py/synchronized_lights.py - Play a single song while synchronizing lights to the music.
* py/hardware_controller.py - Useful for verifying your hardware configuration (blink all lights, turn them on / off, etc...).
* py/check_sms.py - Check sms messages from a google voice account to allow for voting for the next song!
* config/* - Configuration files go here.
* crontab/synchronized_lights - Add these via 'sudo crontab -e' to start / stop the lightshow automatically
* logs/* - Log files will be output here.
* bin/* - Various bash scripts / tools to aid in playing songs, controlling volume, etc...

Contributors
============

A huge thanks to all those that have contributed to the Lightshow Pi codebase:

* Todd Giles
* Chris Usey
* Ryan Jennings
* Sean Millar
* Scott Driscoll