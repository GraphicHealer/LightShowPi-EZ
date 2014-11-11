#
# Playlist generator for LightshowPi
# Author: Eric Higdon (mrbassman.10@gmail.com)
#
# How To:
#	cd to the location of the playlist script (i.e. "lightshowpi/tools/generatePlaylist")
#	run "python generatePlaylist.py"
#	Enter the path to the folder of songs which you desire a playlist for then press <enter> (i.e. "/home/pi/lightshowpi/music/sample")
#	Playlist file will be created in the folder 
# 		Paths are absolute. Include the whole path to the songs folder. (i.e. "/home/pi/lightshowpi/music/christmas")

import os

location = raw_input("Enter the path to the folder of songs:")
songEntry = ""

for song in os.listdir(location):
	if not str(song).startswith("."):
		if str(song).endswith(".mp3"):
			songEntry +=  str(song).replace("_", " ").replace("-", " - ").replace(".mp3", "")
			songEntry += "	" + location + "/"
			songEntry += song + "\r\n"

print "Creating playlist file"
playlistFile = open(location + "/.playlist", "w+")
playlistFile.write(songEntry)
playlistFile.close()
print "Playlist created"
