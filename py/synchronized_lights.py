#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Todd Giles (todd@lightshowpi.org)
# Author: Chris Usey (chris.usey@gmail.com)
# Author: Ryan Jennings
# Author: Paul Dunn (dunnsept@gmail.com)
# Author: Tom Enos (tomslick.ca@gmail.com)

"""Play any audio file and synchronize lights to the music

When executed, this script will play an audio file, as well as turn on
and off N channels of lights to the music (by default the first 8 GPIO
channels on the Raspberry Pi), based upon music it is playing. Many
types of audio files are supported (see decoder.py below), but it has
only been tested with wav and mp3 at the time of this writing.

The timing of the lights turning on and off is based upon the frequency
response of the music being played.  A short segment of the music is
analyzed via FFT to get the frequency response across each defined
channel in the audio range.  Each light channel is then faded in and
out based upon the amplitude of the frequency response in the 
corresponding audio channel.  Fading is accomplished with a software 
PWM output.  Each channel can also be configured to simply turn on and
off as the frequency response in the corresponding channel crosses a 
threshold.

FFT calculation can be CPU intensive and in some cases can adversely
affect playback of songs (especially if attempting to decode the song
as well, as is the case for an mp3).  For this reason, the FFT 
calculations are cached after the first time a new song is played.
The values are cached in a gzipped text file in the same location as the
song itself.  Subsequent requests to play the same song will use the
cached information and not recompute the FFT, thus reducing CPU
utilization dramatically and allowing for clear music playback of all
audio file types.

Recent optimizations have improved this dramatically and most users are
no longer reporting adverse playback of songs even on the first 
playback.

Sample usage:
To play an entire list -
sudo python synchronized_lights.py --playlist=/home/pi/music/.playlist

To play a specific song -
sudo python synchronized_lights.py --file=/home/pi/music/jingle_bells.mp3

Third party dependencies:

alsaaudio: for audio input/output 
    http://pyalsaaudio.sourceforge.net/

decoder.py: decoding mp3, ogg, wma, ... 
    https://pypi.python.org/pypi/decoder.py/1.5XB

numpy: for FFT calculation
    http://www.numpy.org/
"""

import ConfigParser
import argparse
import atexit
import audioop
from collections import deque
import cPickle
import errno
import json
import logging as log
import os
import random
import subprocess
import signal
import stat
import sys
import time
import wave
import curses
import bright_curses
import mutagen
from Queue import Queue, Empty
from threading import Thread

import alsaaudio as aa
import decoder
import numpy as np
from numpy import where, clip, round, nan_to_num

import Platform
import fft
from prepostshow import PrePostShow
import RunningStats


# Make sure SYNCHRONIZED_LIGHTS_HOME environment variable is set
HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")

if not HOME_DIR:
    print("Need to setup SYNCHRONIZED_LIGHTS_HOME environment variable, see readme")
    sys.exit()

LOG_DIR = HOME_DIR + '/logs'

# logging levels
levels = {'DEBUG': log.DEBUG,
          'INFO': log.INFO,
          'WARNING': log.WARNING,
          'ERROR': log.ERROR,
          'CRITICAL': log.CRITICAL}

# Arguments
parser = argparse.ArgumentParser()
parser.add_argument('--log', default='INFO',
                    help='Set the logging level. levels:INFO, DEBUG, WARNING, ERROR, CRITICAL')

file_group = parser.add_mutually_exclusive_group()
file_group.add_argument('--playlist', default="playlist_path",
                        help='Playlist to choose song from.')
file_group.add_argument('--file', help='path to the song to play (required if no '
                                       'playlist is designated)')

cache_group = parser.add_mutually_exclusive_group()
cache_group.add_argument('--readcache', type=bool, default=True,
                         help='read light timing from cache if available. Default: true')
cache_group.add_argument('--createcache', action="store_true",
                         help='create light timing cache without audio playback or lightshow.')

if parser.parse_args().createcache:
    parser.set_defaults(readcache=False)

# Setup log file
log.basicConfig(filename=LOG_DIR + '/music_and_lights.play.dbg',
                format='[%(asctime)s] %(levelname)s {%(pathname)s:%(lineno)d} - %(message)s',
                level=log.INFO)
level = levels.get(parser.parse_args().log.upper())
log.getLogger().setLevel(level)

# import hardware_controller
import hardware_controller

hc = hardware_controller.Hardware()

# get copy of configuration manager
cm = hc.cm

parser.set_defaults(playlist=cm.lightshow.playlist_path)
args = parser.parse_args()


class Lightshow(object):
    def __init__(self):
        self.stream = None
        self.fm_process = None
        self.streaming = None
        self.sample_rate = None
        self.num_channels = None
        self.music_file = None
        self.fft_calc = None
        self.light_delay = None
        self.cache_found = None
        self.cache_matrix = None
        self.cache_filename = None
        self.config_filename = None
        self.song_filename = None
        self.terminal = None

        self.output = lambda raw_data: None

        self.mean = np.array([12.0 for _ in range(cm.hardware.gpio_len)], dtype='float32')
        self.std = np.array([1.5 for _ in range(cm.hardware.gpio_len)], dtype='float32')

        self.attenuate_pct = cm.lightshow.attenuate_pct
        self.sd_low = cm.lightshow.SD_low
        self.sd_high = cm.lightshow.SD_high

        self.decay_factor = cm.lightshow.decay_factor
        self.decay = np.zeros(cm.hardware.gpio_len, dtype='float32')
        self.physical_gpio_len = cm.hardware.physical_gpio_len
        self.network = hc.network
        self.server = self.network.networking == 'server'
        self.client = self.network.networking == "client"

        if cm.lightshow.use_fifo:
            if os.path.exists(cm.lightshow.fifo):
                os.remove(cm.lightshow.fifo)
            os.mkfifo(cm.lightshow.fifo, 0777)

        self.chunk_size = cm.audio_processing.chunk_size  # Use a multiple of 8 

        atexit.register(self.exit_function)

        # Remove traceback on Ctrl-C
        signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))
        signal.signal(signal.SIGTERM, lambda x, y: sys.exit(0))

        if cm.terminal.enabled:
            self.terminal = bright_curses.BrightCurses(cm.terminal)
            curses.wrapper(self.launch_curses)

    def exit_function(self):
        """atexit function"""
        if self.server:
            self.network.set_playing()
            self.network.broadcast([0. for _ in range(cm.hardware.gpio_len)])
            time.sleep(1)
            self.network.unset_playing()

        hc.clean_up()

        if cm.fm.enabled:
            self.fm_process.kill()

        if self.network.network_stream:
            self.network.close_connection()

        if cm.lightshow.mode == 'stream-in':
            try:
                self.streaming.stdin.write("q")
            except IOError:
                pass
            os.kill(self.streaming.pid, signal.SIGINT)
            if cm.lightshow.use_fifo:
                os.unlink(cm.lightshow.fifo)

    def update_lights(self, matrix):
        """Update the state of all the lights

        Update the state of all the lights based upon the current
        frequency response matrix

        :param matrix: row of data from cache matrix
        :type matrix: list
        """
        brightness = matrix - self.mean + (self.std * 0.5)
        brightness = (brightness / (self.std * (self.sd_low + self.sd_high))) \
            * (1.0 - (self.attenuate_pct / 100.0))

        # insure that the brightness levels are in the correct range
        brightness = clip(brightness, 0.0, 1.0)
        # brightness = round(brightness, decimals=3)
        brightness = nan_to_num(brightness)

        # calculate light decay rate if used
        if self.decay_factor > 0:
            self.decay = where(self.decay <= brightness,
                               brightness,
                               self.decay)

            brightness = where(self.decay <= brightness,
                               brightness,
                               self.decay)

            self.decay = where(self.decay - self.decay_factor > 0,
                               self.decay - self.decay_factor,
                               0)

        # broadcast to clients if in server mode
        if self.server:
            self.network.broadcast(brightness)

        if self.terminal:
            self.terminal.curses_render(brightness)
            return

        # in the instance a single channel is defined convert scalar back into array
        if not hasattr(brightness, "__len__"):
            brightness = np.array([brightness])

        for pin in range(len(brightness[:self.physical_gpio_len])):
            hc.set_light(pin, True, brightness[pin])

        if hc.led:
            if cm.led.led_channel_configuration == "EXTEND":
                leds = brightness[self.physical_gpio_len:]
            else:
                leds = brightness[:cm.hardware.gpio_len]

            for led_instance in hc.led:
                led_instance.write_all(leds)

    def set_fm(self):
        pi_version = Platform.pi_version()
        srate = str(int(self.sample_rate / (1 if self.num_channels > 1 else 2)))

        fm_command = ["sudo",
                      cm.home_dir + "/bin/pifm",
                      "-",
                      cm.fm.frequency,
                      srate,
                      "stereo" if self.num_channels > 1 else "mono"]

        if pi_version >= 2:
            fm_command = ["sudo",
                          cm.home_dir + "/bin/pi_fm_rds",
                          "-audio", "-", "-freq",
                          cm.fm.frequency,
                          "-srate",
                          srate,
                          "-nochan",
                          "2" if self.num_channels > 1 else "1"]

        log.info("Sending output as fm transmission")

        with open(os.devnull, "w") as dev_null:
            self.fm_process = subprocess.Popen(fm_command,
                                               stdin=subprocess.PIPE,
                                               stdout=dev_null)
        self.output = lambda raw_data: self.fm_process.stdin.write(raw_data)

    def set_audio_device(self):

        if cm.fm.enabled:
            self.set_fm()

        elif cm.lightshow.audio_out_card is not '':
            if cm.lightshow.mode == 'stream-in':
                self.num_channels = 2

            output_device = aa.PCM(aa.PCM_PLAYBACK, aa.PCM_NORMAL, cm.lightshow.audio_out_card)
            output_device.setchannels(self.num_channels)
            output_device.setrate(self.sample_rate)
            output_device.setformat(aa.PCM_FORMAT_S16_LE)
            output_device.setperiodsize(self.chunk_size)

            self.output = lambda raw_data: output_device.write(raw_data)

    def set_audio_source(self):
        stream_reader = None
        outq = None

        if cm.lightshow.mode == 'audio-in':
            # Open the input stream from default input device
            self.streaming = aa.PCM(aa.PCM_CAPTURE, aa.PCM_NORMAL, cm.lightshow.audio_in_card)
            self.streaming.setchannels(self.num_channels)
            self.streaming.setformat(aa.PCM_FORMAT_S16_LE)  # Expose in config if needed
            self.streaming.setrate(self.sample_rate)
            self.streaming.setperiodsize(self.chunk_size)

            stream_reader = lambda: self.streaming.read()[-1]

        elif cm.lightshow.mode == 'stream-in':

            outq = Queue()

            if cm.lightshow.use_fifo:
                self.streaming = subprocess.Popen(cm.lightshow.stream_command_string,
                                                  stdin=subprocess.PIPE,
                                                  stdout=subprocess.PIPE,
                                                  preexec_fn=os.setsid)
                io = os.open(cm.lightshow.fifo, os.O_RDONLY | os.O_NONBLOCK)
                stream_reader = lambda: os.read(io, self.chunk_size)
                outthr = Thread(target=self.enqueue_output, args=(self.streaming.stdout, outq))
            else:
                # Open the input stream from command string
                self.streaming = subprocess.Popen(cm.lightshow.stream_command_string,
                                                  stdin=subprocess.PIPE,
                                                  stdout=subprocess.PIPE,
                                                  stderr=subprocess.PIPE)
                stream_reader = lambda: self.streaming.stdout.read(self.chunk_size)
                outthr = Thread(target=self.enqueue_output, args=(self.streaming.stderr, outq))

            outthr.daemon = True
            outthr.start()

        return stream_reader,outq

    def audio_in(self):
        """Control the lightshow from audio coming in from a real time audio"""

        self.sample_rate = cm.lightshow.input_sample_rate
        self.num_channels = cm.lightshow.input_channels

        stream_reader,outq = self.set_audio_source()

        log.debug("Running in %s mode - will run until Ctrl+C is pressed" % cm.lightshow.mode)
        print "Running in %s mode, use Ctrl+C to stop" % cm.lightshow.mode

        # setup light_delay.
        chunks_per_sec = ((16 * self.num_channels * self.sample_rate) / 8) / self.chunk_size
        light_delay = int(cm.lightshow.light_delay * chunks_per_sec)
        matrix_buffer = deque([], 1000)

        self.set_audio_device()

        # Start with these as our initial guesses - will calculate a rolling mean / std
        # as we get input data.
        # preload running_stats to avoid errors, and give us a show that looks
        # good right from the start
        count = 2
        running_stats = RunningStats.Stats(cm.hardware.gpio_len)
        running_stats.preload(self.mean, self.std, count)

        hc.initialize()
        fft_calc = fft.FFT(self.chunk_size,
                           self.sample_rate,
                           cm.hardware.gpio_len,
                           cm.audio_processing.min_frequency,
                           cm.audio_processing.max_frequency,
                           cm.audio_processing.custom_channel_mapping,
                           cm.audio_processing.custom_channel_frequencies,
                           1)

        if self.server:
            self.network.set_playing()

        songcount = 0 

        # Listen on the audio input device until CTRL-C is pressed
        while True:

            if cm.lightshow.mode == 'stream-in':
                try:
                    streamout = outq.get_nowait().strip('\n\r')
                except Empty:
                    pass
                else:
                    print streamout
                    if cm.lightshow.stream_song_delim in streamout:
                        songcount+=1
                        if cm.lightshow.songname_command:
                            streamout = streamout.replace('\033[2K','')
                            streamout = streamout.replace(cm.lightshow.stream_song_delim,'')
                            streamout = streamout.replace('"','')
                            os.system(cm.lightshow.songname_command + ' "Now Playing ' + streamout + '"')

                    if cm.lightshow.stream_song_exit_count > 0 and songcount > cm.lightshow.stream_song_exit_count:
                        break

            try:
                data = stream_reader()

            except OSError as err:
                if err.errno == errno.EAGAIN or err.errno == errno.EWOULDBLOCK:
                    continue
            try:
                self.output(data)
            except aa.ALSAAudioError:
                continue

            if len(data):
                # if the maximum of the absolute value of all samples in
                # data is below a threshold we will disregard it
                audio_max = audioop.max(data, 2)
                if audio_max < 250:
                    # we will fill the matrix with zeros and turn the lights off
                    matrix = np.zeros(cm.hardware.gpio_len, dtype="float32")
                    log.debug("below threshold: '" + str(audio_max) + "', turning the lights off")
                else:
                    matrix = fft_calc.calculate_levels(data)
                    running_stats.push(matrix)
                    self.mean = running_stats.mean()
                    self.std = running_stats.std()

                matrix_buffer.appendleft(matrix)

                if len(matrix_buffer) > light_delay:
                    matrix = matrix_buffer[light_delay]
                    self.update_lights(matrix)

    def load_custom_config(self):
        """
        Load custom configuration settings for file config_filename
        """

        """
        example usage
        your song
        carol-of-the-bells.mp3

        First run your playlist (or single files) to create your sync files.  This will
        create a file in the same directory as your music file.
        .carol-of-the-bells.mp3.cfg

        DO NOT EDIT THE existing section [fft], it will cause your sync files to be ignored.

        If you want to use an override you need to add the appropriate section
        The add the options you wish to use, but do not add an option you do not
        want to use, as this will set that option to None and could crash your lightshow.
        Look at defaults.cfg for exact usages of each option

        [custom_lightshow]
        always_on_channels =
        always_off_channels =
        invert_channels =
        preshow_configuration =
        preshow_script =
        postshow_configuration =
        postshow_script =

        [custom_audio_processing]
        min_frequency =
        max_frequency =
        custom_channel_mapping =
        custom_channel_frequencies =

        Note: DO NOT EDIT THE existing section [fft]

        Note: If you use any of the options in "custom_audio_processing" your sync files will be
              automatically regenerated after every change.  This is normal as your sync file needs
              to match these new settings.  After they have been regenerated you will see that they
              now match the settings [fft], and you will not have to regenerate then again.  Unless
              you make more changes again.

        Note: Changes made in "custom_lightshow" do not affect the sync files, so you will not need
              to regenerate them after making changes.
        """
        if os.path.isfile(self.config_filename):
            config = ConfigParser.RawConfigParser(allow_no_value=True)
            with open(self.config_filename) as f:
                config.readfp(f)

                if config.has_section('custom_lightshow'):
                    lsc = "custom_lightshow"

                    always_on = "always_on_channels"
                    if config.has_option(lsc, always_on):
                        hc.always_on_channels = map(int, config.get(lsc, always_on).split(","))

                    always_off = "always_off_channels"
                    if config.has_option(lsc, always_off):
                        hc.always_off_channels = map(int, config.get(lsc, always_off).split(","))

                    inverted = "invert_channels"
                    if config.has_option(lsc, inverted):
                        hc.inverted_channels = map(int, config.get(lsc, inverted).split(","))

                    # setup up custom preshow
                    has_preshow_configuration = config.has_option(lsc, 'preshow_configuration')
                    has_preshow_script = config.has_option(lsc, 'preshow_script')

                    if has_preshow_configuration or has_preshow_script:
                        preshow = None
                        try:
                            preshow_configuration = config.get(lsc, 'preshow_configuration')
                        except ConfigParser.NoOptionError:
                            preshow_configuration = None
                        try:
                            preshow_script = config.get(lsc, 'preshow_script')
                        except ConfigParser.NoOptionError:
                            preshow_script = None

                        if preshow_configuration and not preshow_script:
                            try:
                                preshow = json.loads(preshow_configuration)
                            except (ValueError, TypeError) as error:
                                msg = "Preshow_configuration not defined or not in JSON format."
                                log.error(msg + str(error))
                        else:
                            if os.path.isfile(preshow_script):
                                preshow = preshow_script

                        cm.lightshow.preshow = preshow

                    # setup postshow
                    has_postshow_configuration = config.has_option(lsc, 'postshow_configuration')
                    has_postshow_script = config.has_option(lsc, 'postshow_script')

                    if has_postshow_configuration or has_postshow_script:
                        postshow = None
                        postshow_configuration = config.get(lsc, 'postshow_configuration')
                        postshow_script = config.get(lsc, 'postshow_script')

                        if postshow_configuration and not postshow_script:
                            try:
                                postshow = json.loads(postshow_configuration)
                            except (ValueError, TypeError) as error:
                                msg = "Postshow_configuration not defined or not in JSON format."
                                log.error(msg + str(error))
                        else:
                            if os.path.isfile(postshow_script):
                                postshow = postshow_script

                        cm.lightshow.postshow = postshow

                if config.has_section('custom_audio_processing'):
                    if config.has_option('custom_audio_processing', 'min_frequency'):
                        cm.audio_processing.min_frequency = \
                            config.getfloat('custom_audio_processing', 'min_frequency')

                    if config.has_option('custom_audio_processing', 'max_frequency'):
                        cm.audio_processing.max_frequency = \
                            config.getfloat('custom_audio_processing', 'max_frequency')

                    if config.has_option('custom_audio_processing', 'custom_channel_mapping'):
                        temp = config.get('custom_audio_processing', 'custom_channel_mapping')
                        cm.audio_processing.custom_channel_mapping = \
                            map(int, temp.split(',')) if temp else 0

                    if config.has_option('custom_audio_processing', 'custom_channel_frequencies'):
                        temp = config.get('custom_audio_processing', 'custom_channel_frequencies')
                        cm.audio_processing.custom_channel_frequencies = \
                            map(int, temp.split(',')) if temp else 0

    def setup_audio(self):
        """Setup audio file

        and setup the output.  device.output is a lambda that will send data to
        fm process or to the specified ALSA sound card
        """
        # Set up audio
        force_header = False

        if any([ax for ax in [".mp4", ".m4a", ".m4b"] if ax in self.song_filename]):
            force_header = True

        self.music_file = decoder.open(self.song_filename, force_header)

        self.sample_rate = self.music_file.getframerate()
        self.num_channels = self.music_file.getnchannels()

        self.fft_calc = fft.FFT(self.chunk_size,
                                self.sample_rate,
                                cm.hardware.gpio_len,
                                cm.audio_processing.min_frequency,
                                cm.audio_processing.max_frequency,
                                cm.audio_processing.custom_channel_mapping,
                                cm.audio_processing.custom_channel_frequencies)

        # setup output device
        self.set_audio_device()

        chunks_per_sec = ((16 * self.num_channels * self.sample_rate) / 8) / self.chunk_size
        self.light_delay = int(cm.lightshow.light_delay * chunks_per_sec)

        # Output a bit about what we're about to play to the logs
        num_frames = str(self.music_file.getnframes() / self.sample_rate)
        log.info("Playing: " + self.song_filename + " (" + num_frames + " sec)")

    def setup_cache(self):
        """Setup the cache_matrix, std and mean

        loading them from a file if it exists, otherwise create empty arrays to be filled
        :raise IOError:
        """
        # create empty array for the cache_matrix
        self.cache_matrix = np.empty(shape=[0, cm.hardware.gpio_len])
        self.cache_found = False

        # The values 12 and 1.5 are good estimates for first time playing back
        # (i.e. before we have the actual mean and standard deviations
        # calculated for each channel).

        self.cache_found = self.fft_calc.compare_config(self.cache_filename)

        if args.readcache:
            # Read in cached fft
            try:
                # compare configuration of cache file to current configuration
                self.cache_found = self.fft_calc.compare_config(self.cache_filename)
                if not self.cache_found:
                    # create empty array for the cache_matrix
                    self.cache_matrix = np.empty(shape=[0, cm.hardware.gpio_len])
                    raise IOError()
                else:
                    # load cache from file using numpy loadtxt
                    self.cache_matrix = np.loadtxt(self.cache_filename)

                # get std from matrix / located at index 0
                self.std = np.array(self.cache_matrix[0])

                # get mean from matrix / located at index 1
                self.mean = np.array(self.cache_matrix[1])

                # delete mean and std from the array
                self.cache_matrix = np.delete(self.cache_matrix, 0, axis=0)
                self.cache_matrix = np.delete(self.cache_matrix, 0, axis=0)

                log.debug("std: " + str(self.std) + ", mean: " + str(self.mean))
            except IOError:
                self.cache_found = self.fft_calc.compare_config(self.cache_filename)
                msg = "Cached sync data song_filename not found: '"
                log.warn(msg + self.cache_filename + "'.  One will be generated.")

    def save_cache(self):
        """
        Save matrix, std, and mean to cache_filename for use during future playback
        """
        # Compute the standard deviation and mean values for the cache
        mean = np.empty(cm.hardware.gpio_len, dtype='float32')
        std = np.empty(cm.hardware.gpio_len, dtype='float32')

        for pin in range(0, cm.hardware.gpio_len):
            std[pin] = np.std([item for item in self.cache_matrix[:, pin] if item > 0])
            mean[pin] = np.mean([item for item in self.cache_matrix[:, pin] if item > 0])

        # Add mean and std to the top of the cache
        self.cache_matrix = np.vstack([mean, self.cache_matrix])
        self.cache_matrix = np.vstack([std, self.cache_matrix])

        # Save the cache using numpy savetxt
        np.savetxt(self.cache_filename, self.cache_matrix)

        # Save fft config
        self.fft_calc.save_config()

        cm_len = str(len(self.cache_matrix))
        log.info("Cached sync data written to '." + self.cache_filename + "' [" + cm_len + " rows]")
        log.info("Cached config data written to '." + self.fft_calc.config_filename)

    def get_song(self):
        """
        Determine the next file to play

        :return: tuple containing 3 strings: song_filename, config_filename, cache_filename
        :rtype: tuple
        """
        play_now = int(cm.get_state('play_now', "0"))
        song_to_play = int(cm.get_state('song_to_play', "0"))
        self.song_filename = args.file

        if args.playlist is not None and args.file is None:
            most_votes = [None, None, []]
            songs = cm.get_playlist(args.playlist)
            for song in songs:
                if len(song[2]) > 0:
                    if len(song[2]) >= len(most_votes[2]):
                        most_votes = song

            if most_votes[0] is not None:
                log.info("Most Votes: " + str(most_votes))
                current_song = most_votes

                # Update playlist with latest votes
                for song in songs:
                    if current_song[0:3] == song[0:3] and len(song) == 3:
                        song.append("playing!")

                # Update playlist file
                cm.write_playlist(songs, args.playlist)

            else:
                # Get a "play now" requested song
                if 0 < play_now <= len(songs):
                    current_song = songs[play_now - 1]
                # Get random song
                elif cm.lightshow.randomize_playlist:
                    current_song = songs[random.randrange(0, len(songs))]
                # Play next song in the lineup
                else:
                    if not (song_to_play <= len(songs) - 1):
                        song_to_play = 0

                    current_song = songs[song_to_play]

                    if (song_to_play + 1) <= len(songs) - 1:
                        next_song = (song_to_play + 1)
                    else:
                        next_song = 0

                    cm.update_state('song_to_play', str(next_song))

            # Get filename to play and store the current song playing in state cfg
            self.song_filename = current_song[1]
            cm.update_state('current_song', str(songs.index(current_song)))

        self.song_filename = self.song_filename.replace("$SYNCHRONIZED_LIGHTS_HOME", cm.home_dir)

        filename = os.path.abspath(self.song_filename)
        self.config_filename = \
            os.path.dirname(filename) + "/." + os.path.basename(self.song_filename) + ".cfg"
        self.cache_filename = \
            os.path.dirname(filename) + "/." + os.path.basename(self.song_filename) + ".sync"

        if cm.lightshow.songname_command:
            metadata = mutagen.File(self.song_filename, easy=True)
            if not metadata is None:
                if "title" in metadata:
                    now_playing = "Now Playing " + metadata["title"][0] + " by " + metadata["artist"][0]
                    os.system(cm.lightshow.songname_command + " \"" + now_playing + "\"")

    def play_song(self):
        """Play the next song from the play list (or --file argument)."""

        # get the next song to play
        self.get_song()

        # load custom configuration from file
        self.load_custom_config()

        # Initialize Lights
        self.network.set_playing()
        hc.initialize()

        # Handle the pre/post show
        play_now = int(cm.get_state('play_now', "0"))

        self.network.unset_playing()

        if not play_now:
            result = PrePostShow('preshow', hc).execute()

            if result == PrePostShow.play_now_interrupt:
                play_now = int(cm.get_state('play_now', "0"))

        self.network.set_playing()

        # Ensure play_now is reset before beginning playback
        if play_now:
            cm.update_state('play_now', "0")
            play_now = 0

        # setup audio file and output device
        self.setup_audio()

        # setup our cache_matrix, std, mean
        self.setup_cache()

        matrix_buffer = deque([], 1000)

        # Process audio song_filename
        row = 0
        data = self.music_file.readframes(self.chunk_size)

        if args.createcache:
            total_frames = self.music_file.getnframes() / 100

            counter = 0
            percentage = 0

            while data != '':
                # Compute FFT in this chunk, and cache results
                matrix = self.fft_calc.calculate_levels(data)

                # Add the matrix to the end of the cache
                self.cache_matrix = np.vstack([self.cache_matrix, matrix])
                data = self.music_file.readframes(self.chunk_size)

                if counter > total_frames:
                    percentage += 1
                    counter = 0

                counter += self.chunk_size

                sys.stdout.write("\rGenerating sync file for :%s %d%%" % (self.song_filename,
                                                                          percentage))
                sys.stdout.flush()

            sys.stdout.write("\rGenerating sync file for :%s %d%%" % (self.song_filename, 100))
            sys.stdout.flush()

            data = ''
            self.cache_found = False
            play_now = False
            print "\nsaving sync file"

        while data != '' and not play_now:
            # output data to sound device
            self.output(data)

            # Control lights with cached timing values if they exist
            matrix = None
            if self.cache_found and args.readcache:
                if row < len(self.cache_matrix):
                    matrix = self.cache_matrix[row]
                else:
                    log.warning("Ran out of cached FFT values, will update the cache.")
                    self.cache_found = False

            if matrix is None:
                # No cache - Compute FFT in this chunk, and cache results
                matrix = self.fft_calc.calculate_levels(data)

                # Add the matrix to the end of the cache
                self.cache_matrix = np.vstack([self.cache_matrix, matrix])

            matrix_buffer.appendleft(matrix)

            if len(matrix_buffer) > self.light_delay:
                matrix = matrix_buffer[self.light_delay]
                self.update_lights(matrix)

            # Read next chunk of data from music song_filename
            data = self.music_file.readframes(self.chunk_size)
            row += 1

            # Load new application state in case we've been interrupted
            cm.load_state()
            play_now = int(cm.get_state('play_now', "0"))

        if not self.cache_found and not play_now:
            self.save_cache()

        # Cleanup the pifm process
        if cm.fm.enabled:
            self.fm_process.kill()

        # check for postshow
        self.network.unset_playing()

        if not play_now:
            PrePostShow('postshow', hc).execute()

        # We're done, turn it all off and clean up things ;)
        hc.clean_up()

    def network_client(self):
        """Network client support

        If in client mode, ignore everything else and just
        read data from the network and blink the lights
        """
        log.info("Network client mode starting")
        print "Network client mode starting..."
        print "press CTRL<C> to end"

        hc.initialize()

        print

        try:
            channels = self.network.channels
            channel_keys = channels.keys()

            while True:
                data = self.network.receive()

                if isinstance(data[0], int):
                    pin = data[0]
                    if pin in channel_keys:
                        hc.set_light(channels[pin], True, float(data[1]))
                    continue

                elif isinstance(data[0], np.ndarray):
                    brightness_levels = data[0]

                else:
                    continue

                for pin in channel_keys:
                    hc.set_light(channels[pin], True, brightness_levels[pin])

        except KeyboardInterrupt:
            log.info("CTRL<C> pressed, stopping")
            print "stopping"

            self.network.close_connection()
            hc.clean_up()

    def launch_curses(self, screen):
        self.terminal.init(screen)

    def enqueue_output(self, out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()


if __name__ == "__main__":
    lightshow = Lightshow()

    # Make sure one of --playlist or --file was specified
    if args.file is None and args.playlist is None:
        print "One of --playlist or --file must be specified"
        sys.exit()

    if "-in" in cm.lightshow.mode:
        lightshow.audio_in()

    elif lightshow.client:
        lightshow.network_client()

    else:
        lightshow.play_song()
