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

# Root check
if [ "$EUID" -ne 0 ]; then
    echo "This must be run as root. usage sudo $0"
    echo "Switching to root enter password if asked"
    sudo su -c "$0 $*"
    exit 
fi

# basic error reporting
function errchk {
    echo "Houston we have a problem....."
    echo "$1 failed with exit code $2"
    exit 1
}

# Defaults to install where install.sh is located
INSTALL_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
BUILD_DIR=${INSTALL_DIR}/build_dir

mkdir -p $BUILD_DIR
cd $BUILD_DIR

# update first
apt-get update

# Check to see if we have git
git --version > /dev/null

if [ $? -eq 1 ]; then
	#Nope, install git
	apt-get install -y git
	
    if [ $? -ne 0 ]; then
        errchk "Installing git" $?
    fi
fi

# install decoder
# http://www.brailleweb.com
wget http://www.brailleweb.com/downloads/decoder-1.5XB-Unix.zip
unzip decoder-1.5XB-Unix.zip
cd decoder-1.5XB-Unix
cp decoder.py codecs.pdc fileinfo.py /usr/lib/python2.7/.

# install mutegen
# rough test to see if it is installed
which mutagen-pony > /dev/null

if [ $? -eq 1 ]; then 
    cd mutagen-1.19
    python setup.py build
    python setup.py install

    if [ $? -ne 0 ]; then
        errchk "Installing mutagen" $?
    fi
fi

# install WiringPi2
cd $BUILD_DIR

git clone git://git.drogon.net/wiringPi
cd wiringPi

./build

if [ $? -ne 0 ]; then
    errchk "Git and configure WiringPi2" $?
fi
cd $BUILD_DIR

# install wiringpi2-Python
apt-get install -y python-dev python-setuptools python-pip python-pip
git clone https://github.com/Gadgetoid/WiringPi2-Python.git
cd WiringPi2-Python
python setup.py install

if [ $? -ne 0 ]; then
    errchk "Installing wiringpi2" $?
fi

# install numpy
# http://www.numpy.org/
cd $BUILD_DIR
apt-get install -y python-numpy

if [ $? -ne 0 ]; then
    errchk "Installing numpy" $?
fi

# install python-alsaaudio
apt-get install -y python-alsaaudio
if [ $? -ne 0 ]; then
    errchk "Installing python-alsaaudio" $?
fi

# install audio encoders
apt-get install -y lame flac faad vorbis-tools

if [ $? -ne 0 ]; then
    errchk "Installing audio-encoders" $?
fi

# install audio encoder ffmpeg (wheezy) or libav-tools (Jessie or OSMC)
version=`cat /etc/*-release | grep 'VERSION_ID' | awk -F \" '{print $2}'`
declare -i version

if [ $version -le 7 ] ; then
    apt-get install -y ffmpeg
else
    apt-get install -y libav-tools

    # create symlink to avconv so the decoder can still work
    echo "creating symlink"
    ln -s /usr/bin/avconv /usr/bin/ffmpeg
fi

if [ $? -ne 0 ]; then
    errchk "Installing ffmpeg or libav-tools" $?
fi  

# Setup environment variables
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

# Install googlevoice and sms depedencies
easy_install simplejson

if [ $? -ne 0 ]; then
    errchk "Installing simplejson"  $?
fi

# Install fixed version of googlevoice
wget -O kkleidal-pygooglevoiceupdate.tar.gz https://kkleidal-pygooglevoiceupdate.googlecode.com/archive/450e372008a2d81aab4061fd387ee74e7797e030.tar.gz
tar xvzf kkleidal-pygooglevoiceupdate.tar.gz
cd kkleidal-pygooglevoiceupdate-450e372008a2
python setup.py install

if [ $? -ne 0 ]; then
    errchk "Installing pygooglevoiceupdate" $?
fi

# install beautiful soup
pip install Beautifulsoup

if [ $? -ne 0 ]; then
    errchk "Installing Beautifulsoup" $?
fi

# Explain to installer how they can test to see if we are working
echo
echo "You may need to reboot your Raspberry Pi before running lightshowPi (sudo reboot)."
echo "Run the following command to test your installation and hardware setup (press CTRL-C to stop the test):"
echo
echo "sudo python $INSTALL_DIR/py/hardware_controller.py --state=flash"
echo
