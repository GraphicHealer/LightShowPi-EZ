#/bin/bash
# Syncronized_lights installer
# Author: Sean Millar sean.millar@gmail.com
# Install assumes this is a Rasberry Pi 
# and python 2.7 is to be used.


#Todo's
#add dependencies for using sms (us Canadians don't get google voice :(  )
#better error hanlding
#clean this up so it looks pretty
#


#Root check
if [ `whoami` != 'root' ]; then
	echo "This must be run as root. usage sudo $0"
	exit 1
fi
#default installation dir
#change to whichever directory to install package to
INSTALL_DIR=/home/pi/lights

mkdir $INSTALL_DIR
cd ${INSTALL_DIR}

BUILD_DIR=${INSTALL_DIR/build_dir
mkdir $BUILD_DIR

cd $BUILD_DIR

#Check to see if we have git
git -v > /dev/null
if [ $? -eq 1 ]; then
	#Nope, install git
	apt-get install -y git
fi


#install decoder
	wget http://www.brailleweb.com/downloads/decoder-1.5XB-Unix.zip
	unzip decoder-1.5XB-Unix.zip
 	cd decoder-1.5.XB-Unix
	cp decoder.py codecs.pdc fileinfo.py ${INSTALL_DIR}/py/.
	
#install mutegen
# rough test to see if it is installed
which mutagen-pony > /dev/null

if [ $? -eq 1 ]; then 
	cd mutagen-1.19
	./setup.py build
	./setup.py install
fi
cd $BUILD_DIR
#install WiringPI2

git clone git://git.drogon.net/wiringPi 
cd wiringPi 
sudo ./build
cd $BUILD_DIR

#install wiringpi2-Python
apt-get install -y python-dev python-setuptools 
git clone https://github.com/Gadgetoid/WiringPi2-Python.git
cd WiringPi2-Python
python setup.py install

cd $BUILD_DIR

#install wiringpi

#install numpy
# http://www.numpy.org/
  	apt-get install -y python-numpy

#install python-alsaaudio
	sudo apt-get install -y python-alsaaudio

#install audio encoders
	sudo apt-get update && sudo apt-get install -y lame flac ffmpeg faad vorbis-tools


#handle state.cfg file missing bug#11
touch $INSTALL_DIR/config/state.cfg


#Setup environment variables
echo "${INSTALL_DIR}" >> /etc/environment
source /etc/environment
echo "Defaults	env_keep="SYNCHRONIZED_LIGHTS_HOME"" >>  /etc/sudoers

#Test to see if we are working 
echo "test installation by doing the following 
cd $INSTALL_DIR

sudo py/hardware_controller.py --state flash

echo "If your lights blinked then this must have worked!"
