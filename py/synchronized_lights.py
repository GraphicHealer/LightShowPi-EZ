#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Todd Giles (todd@lightshowpi.com)
# Author: Chris Usey (chris.usey@gmail.com)
# Author: Ryan Jennings
# Author: Paul Dunn (dunnsept@gmail.com)

"""Play any audio file and synchronize lights to the music

When executed, this script will play an audio file, as well as turn on
and off N channels of lights to the music (by default the first 8 GPIO
channels on the Rasberry Pi), based upon music it is playing. Many
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
cacluations are cached after the first time a new song is played.
The values are cached in a gzip'd text file in the same location as the
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

numpy: for FFT calcuation 
    http://www.numpy.org/
"""

import argparse
import atexit
import csv
import fcntl
import logging
import os
import random
import subprocess
import sys
import wave
import alsaaudio as aa

import decoder
import numpy as np

import fft
import configuration_manager as cm
import hardware_controller as hc
from prepostshow import PrePostShow


# Configurations - TODO(todd): Move more of this into configuration manager
_CONFIG = cm.CONFIG
_MODE = cm.lightshow()['mode']
_MIN_FREQUENCY = _CONFIG.getfloat('audio_processing', 'min_frequency')
_MAX_FREQUENCY = _CONFIG.getfloat('audio_processing', 'max_frequency')
_RANDOMIZE_PLAYLIST = _CONFIG.getboolean('lightshow', 'randomize_playlist')

try:
    _CUSTOM_CHANNEL_MAPPING = [int(channel) for channel in
                               _CONFIG.get('audio_processing',
                                           'custom_channel_mapping').split(',')]
except ValueError:
    _CUSTOM_CHANNEL_MAPPING = 0

try:
    _CUSTOM_CHANNEL_FREQUENCIES = [int(channel) for channel in
                                   _CONFIG.get('audio_processing',
                                               'custom_channel_frequencies').split(',')]
except ValueError:
    _CUSTOM_CHANNEL_FREQUENCIES = 0

_PLAYLIST_PATH = cm.lightshow()['playlist_path'].replace('$SYNCHRONIZED_LIGHTS_HOME', cm.HOME_DIR)

_usefm = _CONFIG.getboolean('audio_processing', 'fm')

if _usefm:
    frequency = _CONFIG.get('audio_processing', 'frequency')
    play_stereo = True
    music_pipe_r, music_pipe_w = os.pipe()

CHUNK_SIZE = 2048  # Use a multiple of 8 (move this to config)


def end_early():
    """atexit function"""
    hc.clean_up()


atexit.register(end_early)


def calculate_channel_frequency(min_frequency, max_frequency, custom_channel_mapping,
                                custom_channel_frequencies):
    """Calculate frequency values

    Calculate frequency values for each channel,
    taking into account custom settings.

    :param min_frequency: lowest frequency for which a channel will be activated
    :type min_frequency: float

    :param max_frequency: max frequency for which a channel will be activated.
    :type max_frequency: float

    :param custom_channel_mapping: custom map of channels to different frequencies
    :type custom_channel_mapping: list | int

    :param custom_channel_frequencies: custom list of frequencies that should be
                                       utilized for each channel
    :type custom_channel_frequencies: list | int

    :return: frequency values for each channel
    :rtype: list
    """

    # How many channels do we need to calculate the frequency for
    if custom_channel_mapping != 0 and len(custom_channel_mapping) == hc.GPIOLEN:
        logging.debug("Custom Channel Mapping is being used: %s", str(custom_channel_mapping))
        channel_length = max(custom_channel_mapping)
    else:
        logging.debug("Normal Channel Mapping is being used.")
        channel_length = hc.GPIOLEN

    logging.debug("Calculating frequencies for %d channels.", channel_length)
    octaves = (np.log(max_frequency / min_frequency)) / np.log(2)
    logging.debug("octaves in selected frequency range ... %s", octaves)
    octaves_per_channel = octaves / channel_length
    frequency_limits = []
    frequency_store = []

    frequency_limits.append(min_frequency)

    if custom_channel_frequencies != 0 and (len(custom_channel_frequencies) >= channel_length + 1):
        logging.debug("Custom channel frequencies are being used")
        frequency_limits = custom_channel_frequencies
    else:
        logging.debug("Custom channel frequencies are not being used")
        for pin in range(1, hc.GPIOLEN + 1):
            frequency_limits.append(frequency_limits[-1]
                                    * 10 ** (3 / (10 * (1 / octaves_per_channel))))
    for pin in range(0, channel_length):
        frequency_store.append((frequency_limits[pin], frequency_limits[pin + 1]))
        logging.debug("channel %d is %6.2f to %6.2f ", pin, frequency_limits[pin],
                      frequency_limits[pin + 1])

    # we have the frequencies now lets map them if custom mapping is defined
    if custom_channel_mapping != 0 and len(custom_channel_mapping) == hc.GPIOLEN:
        frequency_map = []

        for pin in range(0, hc.GPIOLEN):
            mapped_channel = custom_channel_mapping[pin] - 1
            mapped_frequency_set = frequency_store[mapped_channel]
            mapped_frequency_set_low = mapped_frequency_set[0]
            mapped_frequency_set_high = mapped_frequency_set[1]
            logging.debug("mapped channel: " + str(mapped_channel) + " will hold LOW: "
                          + str(mapped_frequency_set_low) + " HIGH: "
                          + str(mapped_frequency_set_high))
            frequency_map.append(mapped_frequency_set)

        return frequency_map
    else:
        return frequency_store


def update_lights(matrix, mean, std):
    """Update the state of all the lights

    Update the state of all the lights based upon the current
    frequency response matrix

    :param matrix: row of data from cache matrix
    :type matrix: list

    :param mean: standard mean of fft values
    :type mean: list

    :param std: standard deviation of fft values
    :type std: list
    """
    for pin in range(0, hc.GPIOLEN):
        # Calculate output pwm, where off is at some portion of the std below
        # the mean and full on is at some portion of the std above the mean.
        brightness = matrix[pin] - mean[pin] + 0.5 * std[pin]
        brightness /= 1.25 * std[pin]
        if brightness > 1.0:
            brightness = 1.0

        if brightness < 0:
            brightness = 0

        if not hc.is_pin_pwm[pin]:
            # If pin is on / off mode we'll turn on at 1/2 brightness
            if brightness > 0.5:
                hc.turn_on_light(pin, True)
            else:
                hc.turn_off_light(pin, True)
        else:
            hc.turn_on_light(pin, True, brightness)


def audio_in():
    """Control the lightshow from audio coming in from a USB audio card"""
    sample_rate = cm.lightshow()['audio_in_sample_rate']
    input_channels = cm.lightshow()['audio_in_channels']

    # Open the input stream from default input device
    stream = aa.PCM(aa.PCM_CAPTURE, aa.PCM_NORMAL, cm.lightshow()['audio_in_card'])
    stream.setchannels(input_channels)
    stream.setformat(aa.PCM_FORMAT_S16_LE)  # Expose in config if needed
    stream.setrate(sample_rate)
    stream.setperiodsize(CHUNK_SIZE)

    logging.debug("Running in audio-in mode - will run until Ctrl+C is pressed")
    print "Running in audio-in mode, use Ctrl+C to stop"

    try:
        hc.initialize()
        frequency_limits = calculate_channel_frequency(_MIN_FREQUENCY,
                                                       _MAX_FREQUENCY,
                                                       _CUSTOM_CHANNEL_MAPPING,
                                                       _CUSTOM_CHANNEL_FREQUENCIES)

        # Start with these as our initial guesses - will calculate a rolling mean / std 
        # as we get input data.
        mean = [12.0 for _ in range(hc.GPIOLEN)]
        std = [0.5 for _ in range(hc.GPIOLEN)]
        recent_samples = np.empty((250, hc.GPIOLEN))
        num_samples = 0

        # Listen on the audio input device until CTRL-C is pressed
        while True:
            length, data = stream.read()

            if length:
                try:
                    matrix = fft.calculate_levels(data,
                                                  CHUNK_SIZE,
                                                  sample_rate,
                                                  frequency_limits,
                                                  hc.GPIOLEN,
                                                  input_channels)
                    if not np.isfinite(np.sum(matrix)):
                        # Bad data --- skip it
                        continue
                except ValueError as error:
                    # TODO(todd): This is most likely occurring due to extra time in calculating
                    #             mean/std every 250 samples which causes more to be read than
                    #             expected the next time around.  Would be good to update mean/std
                    #             in separate thread to avoid this --- but for now, skip it when
                    #             we run into this error is good enough ;)
                    logging.debug("skipping update: " + str(error))
                    continue

                update_lights(matrix, mean, std)

                # Keep track of the last N samples to compute a running std / mean
                #
                # TODO(todd): Look into using this algorithm to compute this on a per sample basis:
                #             http://www.johndcook.com/blog/standard_deviation/
                if num_samples >= 250:
                    no_connection_ct = 0

                    for pin in range(0, hc.GPIOLEN):
                        mean[pin] = np.mean([item for item in recent_samples[:, pin] if item > 0])
                        std[pin] = np.std([item for item in recent_samples[:, pin] if item > 0])

                        # Count how many channels are below 10, 
                        # if more than 1/2, assume noise (no connection)
                        if mean[pin] < 10.0:
                            no_connection_ct += 1

                    # If more than 1/2 of the channels appear to be not connected, turn all off
                    if no_connection_ct > hc.GPIOLEN / 2:
                        logging.debug("no input detected, turning all lights off")
                        mean = [20 for _ in range(hc.GPIOLEN)]
                    else:
                        logging.debug("std: " + str(std) + ", mean: " + str(mean))
                    num_samples = 0
                else:
                    for pin in range(0, hc.GPIOLEN):
                        recent_samples[num_samples][pin] = matrix[pin]
                    num_samples += 1

    except KeyboardInterrupt:
        pass

    finally:
        print "\nStopping"
        hc.clean_up()


# TODO(todd): Refactor more of this to make it more readable / modular.
def play_song():
    """Play the next song from the play list (or --file argument)."""
    song_to_play = int(cm.get_state('song_to_play', "0"))
    play_now = int(cm.get_state('play_now', "0"))

    # Arguments
    parser = argparse.ArgumentParser()
    filegroup = parser.add_mutually_exclusive_group()
    filegroup.add_argument('--playlist', default=_PLAYLIST_PATH,
                           help='Playlist to choose song from.')
    filegroup.add_argument('--file', help='path to the song to play (required if no '
                                          'playlist is designated)')

    parser.add_argument('--readcache', type=int, default=1,
                        help='read light timing from cache if available. Default: true')
    args = parser.parse_args()

    # Make sure one of --playlist or --file was specified
    if args.file is None and args.playlist is None:
        print "One of --playlist or --file must be specified"
        sys.exit()

    # Initialize Lights
    hc.initialize()

    # Handle the pre/post show
    if not play_now:
        result = PrePostShow('preshow', hc).execute()

        if result == PrePostShow.play_now_interrupt:
            play_now = int(cm.get_state('play_now', "0"))

    # Determine the next file to play
    song_filename = args.file
    if args.playlist is not None and args.file is None:
        most_votes = [None, None, []]

        with open(args.playlist, 'rb') as playlist_fp:
            fcntl.lockf(playlist_fp, fcntl.LOCK_SH)
            playlist = csv.reader(playlist_fp, delimiter='\t')
            songs = []

            for song in playlist:
                if len(song) < 2 or len(song) > 4:
                    logging.error('Invalid playlist.  Each line should be in the form: '
                                  '<song name><tab><path to song>')
                    sys.exit()
                elif len(song) == 2:
                    song.append(set())
                else:
                    song[2] = set(song[2].split(','))
                    if len(song) == 3 and len(song[2]) >= len(most_votes[2]):
                        most_votes = song
                songs.append(song)

            fcntl.lockf(playlist_fp, fcntl.LOCK_UN)

        if most_votes[0] is not None:
            logging.info("Most Votes: " + str(most_votes))
            current_song = most_votes

            # Update playlist with latest votes
            with open(args.playlist, 'wb') as playlist_fp:
                fcntl.lockf(playlist_fp, fcntl.LOCK_EX)
                writer = csv.writer(playlist_fp, delimiter='\t')

                for song in songs:
                    if current_song == song and len(song) == 3:
                        song.append("playing!")

                    if len(song[2]) > 0:
                        song[2] = ",".join(song[2])
                    else:
                        del song[2]

                writer.writerows(songs)
                fcntl.lockf(playlist_fp, fcntl.LOCK_UN)

        else:
            # Get a "play now" requested song
            if 0 < play_now <= len(songs):
                current_song = songs[play_now - 1]
            # Get random song
            elif _RANDOMIZE_PLAYLIST:
                # Use python's random.randrange() to get a random song
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
        song_filename = current_song[1]
        cm.update_state('current_song', str(songs.index(current_song)))

    song_filename = song_filename.replace("$SYNCHRONIZED_LIGHTS_HOME", cm.HOME_DIR)

    # Ensure play_now is reset before beginning playback
    if play_now:
        cm.update_state('play_now', "0")
        play_now = 0

    # Set up audio
    if song_filename.endswith('.wav'):
        music_file = wave.open(song_filename, 'r')
    else:
        music_file = decoder.open(song_filename)

    sample_rate = music_file.getframerate()
    num_channels = music_file.getnchannels()

    if _usefm:
        logging.info("Sending output as fm transmission")
        output = None

        with open(os.devnull, "w") as dev_null:
            # play_stereo is always True as coded, Should it be changed to
            # an option in the config file?
            fm_process = subprocess.Popen(["sudo",
                                           cm.HOME_DIR + "/bin/pifm",
                                           "-",
                                           str(frequency),
                                           "44100",
                                           "stereo" if play_stereo else "mono"],
                                          stdin=music_pipe_r,
                                          stdout=dev_null)
    else:
        fm_process = None
        output = aa.PCM(aa.PCM_PLAYBACK, aa.PCM_NORMAL)
        output.setchannels(num_channels)
        output.setrate(sample_rate)
        output.setformat(aa.PCM_FORMAT_S16_LE)
        output.setperiodsize(CHUNK_SIZE)

    logging.info("Playing: " + song_filename + " (" + str(music_file.getnframes() / sample_rate)
                 + " sec)")

    # Output a bit about what we're about to play to the logs
    song_filename = os.path.abspath(song_filename)

    # create empty array for the cache_matrix
    cache_matrix = np.empty(shape=[0, hc.GPIOLEN])
    cache_found = False
    cache_filename = os.path.dirname(song_filename) + \
        "/." + os.path.basename(song_filename) + ".sync"

    # The values 12 and 1.5 are good estimates for first time playing back 
    # (i.e. before we have the actual mean and standard deviations 
    # calculated for each channel).
    mean = [12.0 for _ in range(hc.GPIOLEN)]
    std = [1.5 for _ in range(hc.GPIOLEN)]

    if args.readcache:
        # Read in cached fft
        try:
            # load cache from file using numpy loadtxt
            cache_matrix = np.loadtxt(cache_filename)
            cache_found = True

            # get std from matrix / located at index 0
            std = np.array(cache_matrix[0])

            # get mean from matrix / located at index 1
            mean = np.array(cache_matrix[1])

            # delete mean and std from the array
            cache_matrix = np.delete(cache_matrix, 0, axis=0)
            cache_matrix = np.delete(cache_matrix, 0, axis=0)

            logging.debug("std: " + str(std) + ", mean: " + str(mean))
        except IOError:
            logging.warn("Cached sync data song_filename not found: '"
                         + cache_filename
                         + "'.  One will be generated.")

    # Process audio song_filename
    row = 0
    data = music_file.readframes(CHUNK_SIZE)
    frequency_limits = calculate_channel_frequency(_MIN_FREQUENCY,
                                                   _MAX_FREQUENCY,
                                                   _CUSTOM_CHANNEL_MAPPING,
                                                   _CUSTOM_CHANNEL_FREQUENCIES)

    while data != '' and not play_now:
        if _usefm:
            os.write(music_pipe_w, data)
        else:
            output.write(data)

        # Control lights with cached timing values if they exist
        matrix = None
        if cache_found and args.readcache:
            if row < len(cache_matrix):
                matrix = cache_matrix[row]
            else:
                logging.warning("Ran out of cached FFT values, will update the cache.")
                cache_found = False

        if matrix is None:
            # No cache - Compute FFT in this chunk, and cache results
            matrix = fft.calculate_levels(data, CHUNK_SIZE, sample_rate, frequency_limits,
                                          hc.GPIOLEN)

            # Add the matrix to the end of the cache 
            cache_matrix = np.vstack([cache_matrix, matrix])

        update_lights(matrix, mean, std)

        # Read next chunk of data from music song_filename
        data = music_file.readframes(CHUNK_SIZE)
        row += 1

        # Load new application state in case we've been interrupted
        cm.load_state()
        play_now = int(cm.get_state('play_now', "0"))

    if not cache_found:
        # Compute the standard deviation and mean values for the cache
        for i in range(0, hc.GPIOLEN):
            std[i] = np.std([item for item in cache_matrix[:, i] if item > 0])
            mean[i] = np.mean([item for item in cache_matrix[:, i] if item > 0])

        # Add mean and std to the top of the cache
        cache_matrix = np.vstack([mean, cache_matrix])
        cache_matrix = np.vstack([std, cache_matrix])

        # Save the cache using numpy savetxt
        np.savetxt(cache_filename, cache_matrix)

        logging.info("Cached sync data written to '." + cache_filename
                     + "' [" + str(len(cache_matrix)) + " rows]")

    # Cleanup the pifm process
    if _usefm:
        fm_process.kill()

    # check for postshow
    PrePostShow('postshow', hc).execute()

    # We're done, turn it all off and clean up things ;)
    hc.clean_up()


if __name__ == "__main__":
    # Log everything to our log file
    # TODO(todd): Add logging configuration options.
    logging.basicConfig(filename=cm.LOG_DIR + '/music_and_lights.play.dbg',
                        format='[%(asctime)s] %(levelname)s {%(pathname)s:%(lineno)d}'
                               ' - %(message)s',
                        level=logging.DEBUG)

    if cm.lightshow()['mode'] == 'audio-in':
        audio_in()
    else:
        play_song()
