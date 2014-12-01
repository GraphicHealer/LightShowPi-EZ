#!/bin/bash
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Syncronized_lights installer
#
# Author: Sean Millar sean.millar@gmail.com
#
# Install assumes this is a Rasberry Pi and python 2.7 is used.


#TODO(sean): Better Error Handling
#TODO(sean): Clean this up so it looks pretty

PATH=$PATH
export PATH
exec > >(tee install.log)

#Root check
function check_uid {
  if [ $UID != 0 ] ; then
    echo "The lightshowpi installer requires root authority"
    echo "If needed enter the password here :"
    sudo $0
    Exit_Command=$?
    exit $Exit_Command
  fi
  return 0
}
check_uid

function errchk {
# basic error reporting
    echo "Houston we have a problem....."
    echo "$1 failed with exit code $2"
    exit 1
}


# Defaults to install where install.sh is located
INSTALL_DIR="$( cd "$(dirname "$0")" ; pwd -P )"

BUILD_DIR=${INSTALL_DIR}/build_dir
mkdir -p $BUILD_DIR
cd $BUILD_DIR

#Check to see if we have git
git --version > /dev/null
if [ $? -eq 1 ]; then
	#Nope, install git
	sudo apt-get install -y git
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
sudo apt-get install -y python-dev python-setuptools
git clone -b modelbplus https://github.com/Gadgetoid/WiringPi2-Python.git
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

#Setup environment variables
ENV_VARIABLE="SYNCHRONIZED_LIGHTS_HOME=${INSTALL_DIR}"
exists=`grep -r "$ENV_VARIABLE" /etc/profile*`
if [ -z "$exists" ]; then
  echo "# Lightshow Pi Home" > /etc/profile.d/lightshowpi.sh
  echo "$ENV_VARIABLE" >> /etc/profile.d/lightshowpi.sh
  echo "export SYNCHRONIZED_LIGHTS_HOME" >> /etc/profile.d/lightshowpi.sh
  echo "" >> /etc/profile.d/lightshowpi.sh
  echo "# Add Lightshow Pi bin directory to path" >> /etc/profile.d/lightshowpi.sh
  echo "PATH=\$PATH:${INSTALL_DIR}/bin" >> /etc/profile.d/lightshowpi.sh
  echo "export PATH" >> /etc/profile.d/lightshowpi.sh

  # Force set this environment variable in this shell (as above doesn't take until reboot)
  export $ENV_VARIABLE
fi
KEEP_EN="Defaults	env_keep="SYNCHRONIZED_LIGHTS_HOME""
exists=`grep "$KEEP_EN" /etc/sudoers`
if [ -z "$exists" ]; then
  echo "$KEEP_EN" >> /etc/sudoers
fi

#Install googlevoice and sms depedencies
sudo easy_install simplejson
if [ $? -ne 0 ]; then
errchk "google voice deps"  $?
fi

#Install fixed version of googlevoice
wget -O google_voice_authfix.zip https://bwpayne-pygooglevoice-auth-fix.googlecode.com/archive/56f4aaf3b1804977205076861e19ef79359bd7dd.zip

unzip google_voice_authfix.zip
cd bwpayne-pygooglevoice-auth-fix-56f4aaf3b180
sudo python setup.py install
if [ $? -ne 0 ]; then
errchk "googlevoice auth fix" $?
fi

#install beautiful soup
sudo easy_install beautifulsoup4

# Explain to installer how they can test to see if we are working
echo
echo "You may need to reboot your Raspberry Pi before running lightshowPi (sudo reboot)."
echo "Run the following command to test your installation and hardware setup (press CTRL-C to stop the test):"
echo
echo "sudo $INSTALL_DIR/py/hardware_controller.py --state flash"
echo