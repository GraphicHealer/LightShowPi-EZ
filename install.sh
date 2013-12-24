#!/bin/bash
# Syncronized_lights installer
# Author: Sean Millar sean.millar@gmail.com
# Install assumes this is a Rasberry Pi 
# and python 2.7 is to be used.


#Todo's
#better error hanlding
#clean this up so it looks pretty
#

PATH=$PATH
export PATH
exec > >(tee install.log)

#Root check
if [ `whoami` != 'root' ]; then
	echo "This must be run as root. usage sudo $0"
	exit 1
fi


function errchk {
# basic error reporting
    echo "Houston we have a problem....."
    echo "$1 failed with exit code $2"
    exit 1
}



#default installation dir
#change to whichever directory to install package to
INSTALL_DIR=/tmp

mkdir $INSTALL_DIR
BUILD_DIR=${INSTALL_DIR}/build_dir
mkdir $BUILD_DIR
cd $BUILD_DIR

#Check to see if we have git
git --version > /dev/null
if [ $? -eq 1 ]; then
	#Nope, install git
	apt-get install -y git
    if [ $? -ne 0 ]; then
        errchk "git" $?
    fi
fi


#install decoder
	wget http://www.brailleweb.com/downloads/decoder-1.5XB-Unix.zip
	unzip decoder-1.5XB-Unix.zip
 	cd decoder-1.5XB-Unix
	cp decoder.py codecs.pdc fileinfo.py /usr/lib/python2.7/.
	
#install mutegen
# rough test to see if it is installed
which mutagen-pony > /dev/null

if [ $? -eq 1 ]; then 
	cd mutagen-1.19
	sudo python setup.py build
	sudo python setup.py install
    if [ $? -ne 0 ]; then
        errchk "mutagen" $?
    fi
fi
cd $BUILD_DIR
#install WiringPI2

git clone git://git.drogon.net/wiringPi 
cd wiringPi 
sudo ./build
    if [ $? -ne 0 ]; then
        errchk "git" $?
    fi
cd $BUILD_DIR

#install wiringpi2-Python
apt-get install -y python-dev python-setuptools 
git clone https://github.com/Gadgetoid/WiringPi2-Python.git
cd WiringPi2-Python
sudo python setup.py install
    if [ $? -ne 0 ]; then
        errchk "wiringpi2" $?
    fi
cd $BUILD_DIR

#install numpy
# http://www.numpy.org/
  	apt-get install -y python-numpy
if [ $? -ne 0 ]; then
errchk "numpy" $?
fi
#install python-alsaaudio
	sudo apt-get install -y python-alsaaudio
if [ $? -ne 0 ]; then
errchk "python-alsaaudio" $?
fi
#install audio encoders
	sudo apt-get update && sudo apt-get install -y lame flac ffmpeg faad vorbis-tools
if [ $? -ne 0 ]; then
errchk "audio-encoders" $?
fi

#handle state.cfg file missing bug#11
touch $INSTALL_DIR/config/state.cfg


#Setup environment variables
echo "${INSTALL_DIR}" >> /etc/environment
source /etc/environment
echo "Defaults	env_keep="SYNCHRONIZED_LIGHTS_HOME"" >>  /etc/sudoers

#Install googlevoice and sms depedencies
sudo easy_install simplejson
if [ $? -ne 0 ]; then
errchk "google voice deps"  $?
fi
sudo easy_install -U pygooglevoice
if [ $? -ne 0 ]; then
errchk "pygooglevoice" $?
fi

wget -O google_voice_authfix.zip https://bwpayne-pygooglevoice-auth-fix.googlecode.com/archive/56f4aaf3b1804977205076861e19ef79359bd7dd.zip

unzip google_voice_authfix.zip
cd bwpayne-pygooglevoice-auth-fix-56f4aaf3b180
sudo python setup.py install
if [ $? -ne 0 ]; then
errchk "googlevoice auth fix" $?
fi

#install beautiful soup
sudo  easy_install beautifulsoup4

#Test to see if we are working
echo "test installation by doing the following" 
cd $INSTALL_DIR

sudo py/hardware_controller.py --state flash

echo "If your lights blinked then this must have worked!"
