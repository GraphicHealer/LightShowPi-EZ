#!/bin/bash
#
# Installation framework for lightshowPi
#
# Support for each individual distribution is 
INSTALL_DIR="$( cd $(dirname $0) ; pwd -P )"
BUILD_DIR=${INSTALL_DIR}/build_dir

# Globals populated below
BASE_DISTRO=
DISTRO=

# Globals populated by distro-specific scripts
INSTALL_COMMAND=
PYTHON_DEPS=
SYSTEM_DEPS=

# Set up file-based logging
exec 1> >(tee install.log)

# Root check
if [ "$EUID" -ne 0 ]; then
    echo 'Install script requires root privileges!'
    if [ -x /usr/bin/sudo ]; then
        echo 'Switching now, enter the password for "'$USER'", if prompted.'
        sudo su -c "$0 $*"
    else
        echo 'Switching now, enter the password for "root"!'
        su root -c "$0 $*"
    fi
    exit $?
fi

#
# Wrapper for informational logging
# Args:
#     All arguments are written to the terminal and log file
log() {
    echo -ne "\e[1;34mlightshowpi \e[m" >&2
    echo -e "[`date`] $@"
}

#
# Checks the return value of the last command to run
# Args:
#     1 - Message to display on failure
verify() {
    if [ $? -ne 0 ]; then
        echo "Encountered a fatal error: $@"
        exit 1
    fi
}

#
# Configure installation process based on Linux distribution
install_init() {
    DISTRO=`awk -F= '$1~/^ID$/ {print $2}' /etc/os-release`
    BASE_DISTRO=`awk -F= '$1=/ID_LIKE/ {print $2}' /etc/os-release`

    all_supported="ls "

    case $DISTRO in
        archarm|raspbian)
            log Configuring installation for detected distro="'$DISTRO'"
            source $INSTALL_DIR/install-scripts/$DISTRO
            verify "Error importing configuration from install-scripts/$DISTRO"
            ;;
        *)
            log Detected unknown distribution. Please verify that "'$DISTRO'" is supported and update this script.
            log To add support for "'$DISTRO'" create a script with that name in "install-scripts"
            exit 1
            ;;
    esac

}


#
# Wrapper function to handle installation of system packages
# Args:
#     1 - Package name
pkginstall() {
    log Installing $1...
    $INSTALL_COMMAND $1
    verify "Installation of package '$1' failed"
}

#
# Wrapper function to handle installation of Python packages
# Args:
#     1 - Package name
pipinstall() {
    log Installing $1 via pip...
    if [ $1 == "numpy" ]; then echo -e "\e[1;33mWARNING:\e[m numpy installation may take up to 30 minutes"; fi
    /usr/bin/yes | pip3 install --upgrade $1
    verify "Installation of Python package '$1' failed"
}

# Prepare the build environment
install_init
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR && cd $BUILD_DIR

# Install system dependencies
log Preparing to install ${#SYSTEM_DEPS[@]} packages on your system...
for _dep in ${SYSTEM_DEPS[@]}; do
    pkginstall $_dep;
done

# Some symlinks that will make life a little easier
# Note that this may (intentionally) clobber Python 3 symlinks in newer OS's
mv /usr/bin/python /usr/bin/python2
mv /usr/bin/pip /usr/bin/pip2
ln -fs `which python3` /usr/bin/python
ln -fs `which pip3` /usr/bin/pip

# Install decoder
log Installing decoder...
pip3 install --upgrade git+https://broken2048@bitbucket.org/broken2048/decoder-v3.py.git
verify "Installation of decoder-1.5XB-Unix failed"

# Install Python dependencies
log Preparing to install ${#PYTHON_DEPS[@]} python packages on your system...
for _dep in ${PYTHON_DEPS[@]}; do
    pipinstall $_dep;
done

log Installing rpi-audio-levels...
pip3 install git+https://broken2048@bitbucket.org/broken2048/rpi-audio-levels.git
verify "Installation of rpi-audio-levels failed"

# Install pygooglevoice
log Installing pygooglevoice...
pip3 install --upgrade git+https://github.com/pettazz/pygooglevoice.git
verify "Installation of pygooglevoice failed"

# Install wiringpipy
log Installing wiringpipy...
pip3 install --upgrade git+https://broken2048@bitbucket.org/broken2048/wiringpipy.git
verify "Installation of wiringpipy failed"

# Optionally add a line to /etc/sudoers
if [ -f /etc/sudoers ]; then
    KEEP_EN="Defaults             env_keep="SYNCHRONIZED_LIGHTS_HOME""
    grep -q "$KEEP_EN" /etc/sudoers
    if [ $? -ne 0 ]; then
        echo "$KEEP_EN" >> /etc/sudoers
    fi
fi

# Set up environment variables
cat <<EOF >/etc/profile.d/lightshowpi.sh
# Lightshow Pi Home
export SYNCHRONIZED_LIGHTS_HOME=${INSTALL_DIR}
# Add Lightshow Pi bin directory to path
export PATH=\$PATH:${INSTALL_DIR}/bin
EOF

# Clean up after ourselves
cd ${INSTALL_DIR} && rm -rf ${BUILD_DIR}

# Print some instructions to the user
cat <<EOF


All done! Reboot your Raspberry Pi before running lightshowPi.
Run the following command to test your installation and hardware setup:

    sudo python $INSTALL_DIR/py/hardware_controller.py --state=flash

EOF
exit 0

