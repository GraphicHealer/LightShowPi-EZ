#!/usr/bin/env python
#
# Author: Todd Giles (todd.giles@gmail.com)
#
# Feel free to use as you'd like, but I'd love to hear back from you on any
# improvements, changes, etc...
#
# Modifications by: Chris Usey (chris.usey@gmail.com)
"""Check SMS messages from a Google Voice account to control the lightshow

When executed, this script will check all the SMS messages from a Google Voice account checking for
either the "help" command, which will cause a help message to be sent back to the original sender,
or a single number indicating which song they are voting for.

When a song is voted for, the playlist file will be updated with the sender's cell phone number to
indicate it has received a vote from that caller.  This also enforces only a single vote per phone
number per s (until that song is played).

See the commands.py file for other commands that are also supported (as well asinstructions on
adding new own commands).

Sample usage:

sudo check_sms.py --playlist=/home/pi/music/.playlist

Third party dependencies:

pygooglevoice: http://sphinxdoc.github.io/pygooglevoice/
Beautiful Soup: http://www.crummy.com/software/BeautifulSoup/

Note, I also had to use the following version of pygooglevoice w/auth fix:
https://code.google.com/r/bwpayne-pygooglevoice-auth-fix/
"""

import argparse
import commands
import csv
import fcntl
import logging
import sys
import time

from bs4 import BeautifulSoup
import configuration_manager as cm
from googlevoice import Voice


# Setup your username and password in ~/.gvoice file as follows:
#
# [auth]
# email=<google voice email address>
# password=<google voice password>
#
VOICE = Voice()
VOICE.login()

def song_played(song):
    '''Send an sms message to each requesting user that their song is now playing'''
    for phonenumber in song[2]:
        VOICE.send_sms(phonenumber, '"' + song[0] + '" is playing!')

# extractsms - taken from http://sphinxdoc.github.io/pygooglevoice/examples.html
# originally written by John Nagle (nagle@animats.com)
def extractsms(htmlsms):
    '''Extract SMS messages from BeautifulSoup tree of Google Voice SMS Html, returning a list of
    dictionaries, one per message.'''
    msgitems = []
    tree = BeautifulSoup(htmlsms)  # parse HTML into tree
    conversations = tree("div", attrs={"id" : True, "class" : "gc-message-unread"}, recursive=False)
    for conversation in conversations:
        #   For each conversation, extract each row, which is one SMS message.
        rows = conversation(attrs={"class" : "gc-message-sms-row"})
        for row in rows:  # for all rows
            #   For each row, which is one message, extract all the fields.
            msgitem = {"id" : conversation["id"]}  # tag this message with conversation ID
            spans = row("span", attrs={"class" : True}, recursive=False)
            for span in spans:  # for all spans in row
                name = span['class'][0].replace('gc-message-sms-', '')
                msgitem[name] = (" ".join(span.findAll(text=True))).strip()  # put text in dict
            msgitems.append(msgitem)  # add msg dictionary to list
    return msgitems

def main():
    '''main'''
    parser = argparse.ArgumentParser()
    parser.add_argument('--playlist',
                        default=cm.lightshow()['playlist_path'].replace("$SYNCHRONIZED_LIGHTS_HOME",
                                                                        cm.HOME_DIR),
                        help='filename with the song playlist, one song per line in the format: '
                             '<song name><tab><path to song>')
    args = parser.parse_args()

    # Log everything to debug log file
    # TODO(toddgiles): Add logging configuration options.
    logging.basicConfig(filename=cm.LOG_DIR + '/music_and_lights.check.dbg',
                        format='[%(asctime)s] %(levelname)s {%(pathname)s:%(lineno)d}'
                        ' - %(message)s',
                        level=logging.DEBUG)

    # Load playlist from file, notifying users of any of their requests that have now played
    logging.info('loading playlist ' + args.playlist)
    with open(args.playlist, 'rb') as playlist_fp:
        fcntl.lockf(playlist_fp, fcntl.LOCK_SH)
        playlist = csv.reader(playlist_fp, delimiter='\t')
        songs = []
        for song in playlist:
            logging.debug(song)
            if len(song) < 2 or len(song) > 4:
                logging.error('Invalid playlist.  Each line should be in the form: '
                             '<song name><tab><path to song>')
                sys.exit()
            elif len(song) == 2:
                song.append(set())
            elif len(song) >= 3:
                # Votes for the song are stored in the 3rd column
                song[2] = set(song[2].split(','))
                if len(song) == 4:
                    # Notification of a song being played is stored in the 4th column
                    song_played(song)
                    del song[3]
                    song[2] = set()
            songs.append(song)
        fcntl.lockf(playlist_fp, fcntl.LOCK_UN)
    logging.info('loaded %d songs from playlist', len(songs))
    cm.set_songs(songs)

    # Parse and act on any new sms messages
    messages = VOICE.sms().messages
    for msg in extractsms(VOICE.sms.html):
        logging.debug(str(msg))
        response = commands.execute(msg['text'], msg['from'])
        if response:
            logging.info('Request: "' + msg['text'] + '" from ' + msg['from'])
            try:
                if isinstance(response, basestring):
                    VOICE.send_sms(msg['from'], response)
                else:
                    # Multiple parts, send them with a delay in hopes to avoid
                    # them being received out of order by the recipient.
                    for part in response:
                        VOICE.send_sms(msg['from'], str(part))
                        time.sleep(2)
            except:
                logging.warn('Error sending sms response (command still executed)', exc_info=1)
            logging.info('Response: "' + str(response) + '"')
        else:
            logging.info('Unknown request: "' + msg['text'] + '" from ' + msg['from'])
            VOICE.send_sms(msg['from'], cm.sms()['unknown_command_response'])

    # Update playlist with latest votes
    with open(args.playlist, 'wb') as playlist_fp:
        fcntl.lockf(playlist_fp, fcntl.LOCK_EX)
        writer = csv.writer(playlist_fp, delimiter='\t')
        for song in songs:
            if len(song[2]) > 0:
                song[2] = ",".join(song[2])
            else:
                del song[2]
        writer.writerows(songs)
        fcntl.lockf(playlist_fp, fcntl.LOCK_UN)

    # Delete all mesages now that we've processed them
    for msg in messages:
        msg.delete(1)

if __name__ == "__main__":
    main()
