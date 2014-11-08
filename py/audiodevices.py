''' you must first have, of course, python 2.7 installed along with pyaudio
from http://people.csail.mit.edu/hubert/pyaudio/
for this script to function.
Make sure that STEREO MIX is enabled in windows
IE: http://www.howtogeek.com/howto/39532/how-to-enable-stereo-mix-in-windows-7-to-record-audio/

Once you have, run this and look for the device number for stereo mix.
You will need to edit stereomix.py for the appropriate device.
Sample output:
0. Microsoft Sound Mapper - Input
1. Stereo Mix (Realtek High Defini
2. FrontMic (Realtek High Definiti
6. Primary Sound Capture Driver

which shows on the test system that device number 1 is stereo mix.
Edit stereomix.py and look for the line
device = 1
and change the number to match your stereo mix
tested on Win 7 and XP only
5-30-14 dunnsept@gmail.com
'''

import pyaudio

# List all audio input devices denoted by having >0 input channels
p = pyaudio.PyAudio()
i = 0
n = p.get_device_count()
print str(n) + " devices found"

while i < n:
    dev = p.get_device_info_by_index(i)
    if dev['maxInputChannels'] > 0:
        print str(i)+'. '+dev['name']
        
    i += 1
 
