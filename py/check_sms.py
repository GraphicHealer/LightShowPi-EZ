#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Todd Giles (todd@lightshowpi.org)
#
# Modifications by: Chris Usey (chris.usey@gmail.com)
# Modifications by: Tom Enos (tomslick.ca@gmail.com)

import argparse
import csv
import fcntl
import logging
import os
import signal
import sys
import time

from BeautifulSoup import BeautifulSoup
from googlevoice import Voice
from googlevoice.util import LoginError, ValidationError
from threading import Thread

import configuration_manager
import commands

cm = configuration_manager.Configuration(True)

logging.basicConfig(filename=configuration_manager.LOG_DIR + '/music_and_lights.check.dbg',
                    format='[%(asctime)s] %(levelname)s {%(pathname)s:%(lineno)d}'
                           ' - %(message)s',
                    level=logging.INFO)


class Sms(Thread):
    """Check SMS messages from a Google Voice account to control the lightshow

    When executed, this script will check all the SMS messages from a Google Voice account checking
    for either the "help" command, which will cause a help message to be sent back to the original
    sender, or a single number indicating which song they are voting for.

    When a song is voted for, the playlist file will be updated with the sender's cell phone number
    to indicate it has received a vote from that caller.  This also enforces only a single vote per
    phone number per s (until that song is played).

    See the commands.py file for other commands that are also supported (as well as instructions on
    adding new own commands).

    Sample usage:

    sudo python check_sms.py --playlist=/home/pi/music/.playlist

    For initial setup:

    sudo python check_sms.py --setup=True

    Third party dependencies:

    pygooglevoice: http://sphinxdoc.github.io/pygooglevoice/
    Beautiful Soup: http://www.crummy.com/software/BeautifulSoup/
    """

    def __init__(self, setup=False):
        super(Sms, self).__init__()
        self.daemon = True
        self.cancelled = False

        if setup:
            self.cancelled = True

        # if not using sms exit
        if not cm.sms.enable:
            self.cancelled = True
            sys.exit()

        levels = {'DEBUG': logging.DEBUG,
                  'INFO': logging.INFO,
                  'WARNING': logging.WARNING,
                  'ERROR': logging.ERROR,
                  'CRITICAL': logging.CRITICAL}

        # set logging level from config or command line if used
        try:
            level = levels.get(args.log.upper(), logging.NOTSET)
        except NameError:
            level = levels.get(cm.sms.log_level, logging.NOTSET)

        logging.getLogger().setLevel(level)

        try:
            self.playlist = args.playlist
        except NameError:
            self.playlist = cm.sms.playlist_path

        self.songs = list()
        logging.info('loading playlist ' + self.playlist)

        self.load_playlist()
        commands.start(cm)
        self.voice = Voice()

    def run(self):
        """Overloaded Thread.run, runs the update
        method once per every 15 seconds."""
        self.login()

        while not self.cancelled:
            try:
                self.update()
            except:
                logging.error(
                    'Error when checking for sms messages, will try again in 15 seconds.',
                    exc_info=1)

            time.sleep(15)

    def cancel(self):
        """End this timer thread"""
        self.cancelled = True

    def update(self):
        """Check for new messages"""
        self.check()

    def login(self):
        """Login to google voice account

        Setup your username and password in ~/.gvoice (or /root/.gvoice when running as root)
        file as follows to avoid being asked for your email and password each time:

        [auth]
        email=<google voice email address>
        password=<google voice password>
        """

        # make sure we are logged in
        # if unable to login wait 30 seconds and try again
        # if unable to login after 3 attempts exit check_sms
        logged_in = False
        attempts = 0
        while not logged_in:
            try:
                self.voice.login()
                logged_in = True
                logging.info("Successfully logged in to Google Voice account")
            except LoginError as error:
                attempts += 1
                if attempts <= 3:
                    time.sleep(30)
                else:
                    logging.critical('Unable to login to Google Voice, Exiting SMS.')
                    self.cancelled = True
                    sys.exit()

    @staticmethod
    def extract_sms(html_sms):
        """Extract SMS messages from BeautifulSoup tree of Google Voice SMS Html,

        returning a list of dictionaries, one per message.

        extract_sms - taken from http://sphinxdoc.github.io/pygooglevoice/examples.html
        originally written by John Nagle (nagle@animats.com)

        :param html_sms: Google Voice SMS Html data
        :type html_sms: BeautifulSoup object

        :return: msg_items
        :rtype: dictionary
        """
        msgitems = []

        # parse HTML into tree
        tree = BeautifulSoup(html_sms)
        conversations = tree.findAll("div", attrs={"id": True}, recursive=False)

        for conversation in conversations:
            # For each conversation, extract each row, which is one SMS message.
            rows = conversation.findAll(attrs={"class": "gc-message-sms-row"})
            # for all rows
            for row in rows:

                # For each row, which is one message, extract all the fields.
                # tag this message with conversation ID
                msgitem = {"id": conversation["id"]}
                spans = row.findAll("span", attrs={"class": True}, recursive=False)

                # for all spans in row
                for span in spans:
                    name = span['class'].replace('gc-message-sms-', '')

                    # put text in dict
                    msgitem[name] = (" ".join(span.findAll(text=True))).strip()

                # add msg dictionary to list
                msgitems.append(msgitem)

        return msgitems

    def load_playlist(self):
        """
        Load playlist from file

        notifying users of any of their requests that are now playing
        """
        with open(self.playlist, 'rb') as playlist_fp:
            fcntl.lockf(playlist_fp, fcntl.LOCK_SH)
            playlist = csv.reader(playlist_fp, delimiter='\t')
            self.songs = list()

            for song in playlist:
                logging.debug(song)

                if len(song) < 2 or len(song) > 4:
                    logging.error('Invalid playlist.  Each line should be in the form: '
                                  '<song name><tab><path to song>')
                    logging.warning('Removing invalid entry')
                    print "Error found in playlist"
                    print "Deleting entry:", song
                    continue
                elif len(song) == 2:
                    song.append(set())
                elif len(song) >= 3:
                    # Votes for the song are stored in the 3rd column
                    song[2] = set(song[2].split(','))

                    if len(song) == 4:
                        # Notification of a song being played is stored in the 4th column
                        # Send an sms message to each requesting user that their song is now playing
                        for phonenumber in song[2]:
                            self.voice.send_sms(phonenumber, '"' + song[0] + '" is playing!')

                        del song[3]
                        song[2] = set()

                self.songs.append(song)

            fcntl.lockf(playlist_fp, fcntl.LOCK_UN)

        logging.info('loaded %d songs from playlist', len(self.songs))
        cm.set_playlist(self.songs)

    def update_playlist(self):
        """Update playlist with latest votes"""
        with open(self.playlist, 'wb') as playlist_fp:
            fcntl.lockf(playlist_fp, fcntl.LOCK_EX)
            writer = csv.writer(playlist_fp, delimiter='\t')
            for song in self.songs:
                if len(song[2]) > 0:
                    song[2] = ",".join(song[2])
                else:
                    del song[2]
            writer.writerows(self.songs)
            fcntl.lockf(playlist_fp, fcntl.LOCK_UN)

    def check(self):
        """Process sms messages

        Download and process all sms messages from a Google Voice account.
        this is executed every 15 seconds
        """
        # load the playlist
        self.load_playlist()

        # Parse and act on any new sms messages
        messages = self.voice.sms().messages
        for msg in self.extract_sms(self.voice.sms.html):
            logging.debug(str(msg))
            response = commands.execute(msg['text'], msg['from'])
            if response:
                logging.info('Request: "' + msg['text'] + '" from ' + msg['from'])

                try:
                    if isinstance(response, basestring):
                        self.voice.send_sms(msg['from'], response)
                    else:
                        # Multiple parts, send them with a delay in hopes to avoid
                        # them being received out of order by the recipient.
                        for part in response:
                            self.voice.send_sms(msg['from'], str(part))
                            time.sleep(2)
                except ValidationError as v_error:
                    logging.warn(
                        str(v_error) + ': Error sending sms response (command still executed)',
                        exc_info=1)

                logging.info('Response: "' + str(response) + '"')
            else:
                logging.info('Unknown request: "' + msg['text'] + '" from ' + msg['from'])
                self.voice.send_sms(msg['from'], cm.sms.unknown_command_response)

        # update the playlist
        self.update_playlist()

        # Delete all messages now that we've processed them
        for msg in messages:
            msg.delete(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--playlist',
                        default=cm.sms.playlist_path,
                        help='filename with the song playlist, one song per line in the format: '
                             '<song name><tab><path to song>')
    parser.add_argument('--setup', default=False,
                        help='use this option to setup the default '
                             'configuration file for Google Voice')
    parser.add_argument('--log', default='INFO',
                        help='Set the logging level. levels:INFO, DEBUG, WARNING, ERROR, CRITICAL')
    args = parser.parse_args()

    check_sms = Sms(args.setup)
    signal.signal(signal.SIGINT, lambda x, y: check_sms.cancel())
    check_sms.start()
    signal.pause()
