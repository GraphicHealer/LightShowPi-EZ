#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Todd Giles (todd@lightshowpi.com)
# Author: Chris Usey (chris.usey@gmail.com)
# Author: Ryan Jennings
"""Play any audio file and synchronize lights to the music

When executed, this script will play an audio file, as well as turn on and off 8 channels
of lights to the music (via the first 8 GPIO channels on the Rasberry Pi), based upon
music it is playing. Many types of audio files are supported (see decoder.py below), but
it has only been tested with wav and mp3 at the time of this writing.

The timing of the lights turning on and off are controlled based upon the frequency response
of the music being played.  A short segment of the music is analyzed via FFT to get the
frequency response across 8 channels in the audio range.  Each light channel is then turned
on or off based upon whether the amplitude of the frequency response in the corresponding
channel has crossed a dynamic threshold.

The threshold for each channel is "dynamic" in that it is adjusted upwards and downwards
during the song play back based upon the frequency response amplitude of the song. This ensures
that soft songs, or even soft portions of songs will still turn all 8 channels on and off
during the song.

FFT calculation is quite CPU intensive and can adversely affect playback of songs (especially if
attempting to decode the song as well, as is the case for an mp3).  For this reason, the timing
values of the lights turning on and off is cached after it is calculated upon the first time a
new song is played.  The values are cached in a gzip'd text file in the same location as
the song itself.  Subsequent requests to play the same song will use the cached information and not
recompute the FFT, thus reducing CPU utilization dramatically and allowing for clear music
playback of all audio file types.

Sample usage:

sudo python synchronized_lights.py --playlist=/home/pi/music/.playlist
<<<<<<< HEAD
<<<<<<< HEAD
=======

To play a specific song -
>>>>>>> f636b6af59fd9133afd977147135fca043d7c4ff
=======
>>>>>>> aeb8a01bc942e80eab316f0ae42788cfa885938c
sudo python synchronized_lights.py --file=/home/pi/music/jingle_bells.mp3

Third party dependencies:

alsaaudio: for audio output - http://pyalsaaudio.sourceforge.net/
decoder.py: decoding mp3, ogg, wma, ... - https://pypi.python.org/pypi/decoder.py/1.5XB
numpy: for FFT calcuation - http://www.numpy.org/
"""

import argparse
import csv
import fcntl
import gzip
import logging
import os
import random
from struct import unpack
import sys
import time
import wave

import alsaaudio as aa
import configuration_manager as cm
import decoder
import hardware_controller as hc
import numpy as np


# Configurations - TODO(todd): Move more of this into configuration manager
_CONFIG = cm.CONFIG
_LIMIT_LIST = [int(lim) for lim in _CONFIG.get('auto_tuning', 'limit_list').split(',')]
_LIMIT_THRESHOLD = _CONFIG.getfloat('auto_tuning', 'limit_threshold')
_LIMIT_THRESHOLD_INCREASE = _CONFIG.getfloat('auto_tuning', 'limit_threshold_increase')
_LIMIT_THRESHOLD_DECREASE = _CONFIG.getfloat('auto_tuning', 'limit_threshold_decrease')
_MAX_OFF_CYCLES = _CONFIG.getfloat('auto_tuning', 'max_off_cycles')
_MIN_FREQUENCY = _CONFIG.getfloat('audio_processing', 'min_frequency')
_MAX_FREQUENCY = _CONFIG.getfloat('audio_processing', 'max_frequency')
_RANDOMIZE_PLAYLIST = _CONFIG.getboolean('lightshow', 'randomize_playlist')
try:
    _CUSTOM_CHANNEL_MAPPING = [int(channel) for channel in
                               _CONFIG.get('audio_processing', 'custom_channel_mapping').split(',')]
except:
    _CUSTOM_CHANNEL_MAPPING = 0
try:
    _CUSTOM_CHANNEL_FREQUENCIES = [int(channel) for channel in
                                   _CONFIG.get('audio_processing',
                                               'custom_channel_frequencies').split(',')]
except:
    _CUSTOM_CHANNEL_FREQUENCIES = 0
try:
    _PLAYLIST_PATH = _CONFIG.get('lightshow', 'playlist_path').replace('$SYNCHRONIZED_LIGHTS_HOME',
                                                                       cm.HOME_DIR)
except:
    _PLAYLIST_PATH = "/home/pi/music/.playlist"
CHUNK_SIZE = 2048  # Use a multiple of 8


def execute_preshow(config):
    '''Execute the "Preshow" for the given preshow configuration'''
    for transition in config['transitions']:
        start = time.time()
        if transition['type'].lower() == 'on':
            hc.turn_on_lights(True)
        else:
            hc.turn_off_lights(True)
        logging.debug('Transition to ' + transition['type'] + ' for '
            + str(transition['duration']) + ' seconds')
        while transition['duration'] > (time.time() - start):
            cm.load_state()  # Force a refresh of state from file
            play_now = int(cm.get_state('play_now', 0))
            if play_now:
                return  # Skip out on the rest of the preshow

            # Check once every ~ .1 seconds to break out
            time.sleep(0.1)

def calculate_channel_frequency(min_frequency, max_frequency, custom_channel_mapping,
                                custom_channel_frequencies):
    '''Calculate frequency values for each channel, taking into account custom settings.'''

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
        for i in range(1, hc.GPIOLEN + 1):
            frequency_limits.append(frequency_limits[-1]
                                    * 10 ** (3 / (10 * (1 / octaves_per_channel))))
    for i in range(0, channel_length):
        frequency_store.append((frequency_limits[i], frequency_limits[i + 1]))
        logging.debug("channel %d is %6.2f to %6.2f ", i, frequency_limits[i],
                      frequency_limits[i + 1])

    # we have the frequencies now lets map them if custom mapping is defined
    if custom_channel_mapping != 0 and len(custom_channel_mapping) == hc.GPIOLEN:
        frequency_map = []
        for i in range(0, hc.GPIOLEN):
            mapped_channel = custom_channel_mapping[i] - 1
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

def piff(val, sample_rate):
    '''Return the power array index corresponding to a particular frequency.'''
    return int(CHUNK_SIZE * val / sample_rate)

# TODO(todd): Move FFT related code into separate file as a library
def calculate_levels(data, sample_rate, frequency_limits):
    '''Calculate frequency response for each channel
    
    Initial FFT code inspired from the code posted here:
    http://www.raspberrypi.org/phpBB3/viewtopic.php?t=35838&p=454041
    
    Optimizations from work by Scott Driscoll:
    http://www.instructables.com/id/Raspberry-Pi-Spectrum-Analyzer-with-RGB-LED-Strip-/
    '''

    # create a numpy array. This won't work with a mono file, stereo only.
    data_stereo = np.frombuffer(data, dtype=np.int16)
    data = np.empty(len(data) / 4)  # data has two channels and 2 bytes per channel
    data[:] = data_stereo[::2]  # pull out the even values, just using left channel

    # if you take an FFT of a chunk of audio, the edges will look like
    # super high frequency cutoffs. Applying a window tapers the edges
    # of each end of the chunk down to zero.
    window = np.hanning(len(data))
    data = data * window

    # Apply FFT - real data
    fourier = np.fft.rfft(data)

    # Remove last element in array to make it the same size as CHUNK_SIZE
    fourier = np.delete(fourier, len(fourier) - 1)

    # Calculate the power spectrum
    power = np.abs(fourier) ** 2

    matrix = [0 for i in range(hc.GPIOLEN)]
    for i in range(hc.GPIOLEN):
        # take the log10 of the resulting sum to approximate how human ears perceive sound levels
        matrix[i] = np.log10(np.sum(power[piff(frequency_limits[i][0], sample_rate)
                                          :piff(frequency_limits[i][1], sample_rate):1]))

    return matrix

# TODO(todd): Refactor this to make it more readable / modular.
def main():
    '''main'''
    song_to_play = int(cm.get_state('song_to_play', 0))
    play_now = int(cm.get_state('play_now', 0))

    # Arguments
    parser = argparse.ArgumentParser()
    filegroup = parser.add_mutually_exclusive_group()
    filegroup.add_argument('--playlist', default=_PLAYLIST_PATH,
                           help='Playlist to choose song from.')
    filegroup.add_argument('--file', help='path to the song to play (required if no'
                           'playlist is designated)')
    parser.add_argument('--readcache', type=int, default=1,
                        help='read light timing from cache if available. Default: true')
    args = parser.parse_args()

    # Log everything to our log file
    # TODO(todd): Add logging configuration options.
    logging.basicConfig(filename=cm.LOG_DIR + '/music_and_lights.play.dbg',
                        format='[%(asctime)s] %(levelname)s {%(pathname)s:%(lineno)d}'
                        ' - %(message)s',
                        level=logging.DEBUG)

    # Make sure one of --playlist or --file was specified
    if args.file == None and args.playlist == None:
        print "One of --playlist or --file must be specified"
        sys.exit()

    # Initialize Lights
    hc.initialize()

    # Only execute preshow if no specific song has been requested to be played right now
    if not play_now:
        execute_preshow(cm.lightshow()['preshow'])

    # Determine the next file to play
    song_filename = args.file
    if args.playlist != None and args.file == None:
        most_votes = [None, None, []]
        current_song = None
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

        if most_votes[0] != None:
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
            # Get random song
            if _RANDOMIZE_PLAYLIST:
                current_song = songs[random.randint(0, len(songs) - 1)]
            # Get a "play now" requested song
            elif play_now > 0 and play_now <= len(songs):
                current_song = songs[play_now - 1]
            # Play next song in the lineup
            else:
                song_to_play = song_to_play if (song_to_play <= len(songs) - 1) else 0
                current_song = songs[song_to_play]
                next_song = (song_to_play + 1) if ((song_to_play + 1) <= len(songs) - 1) else 0
                cm.update_state('song_to_play', next_song)

        # Get filename to play and store the current song playing in state cfg
        song_filename = current_song[1]
        cm.update_state('current_song', songs.index(current_song))

    song_filename = song_filename.replace("$SYNCHRONIZED_LIGHTS_HOME", cm.HOME_DIR)

    # Ensure play_now is reset before beginning playback
    if play_now:
        cm.update_state('play_now', 0)
        play_now = 0

    # Initialize FFT stats
    matrix = [0 for _ in range(hc.GPIOLEN)]
    offct = [0 for _ in range(hc.GPIOLEN)]

    # Build the limit list
    if len(_LIMIT_LIST) == 1:
        limit = [_LIMIT_LIST[0] for _ in range(hc.GPIOLEN)]
    else:
        limit = _LIMIT_LIST

    # Set up audio
    if song_filename.endswith('.wav'):
        musicfile = wave.open(song_filename, 'r')
    else:
        musicfile = decoder.open(song_filename)

    sample_rate = musicfile.getframerate()
    num_channels = musicfile.getnchannels()
    output = aa.PCM(aa.PCM_PLAYBACK, aa.PCM_NORMAL)
    output.setchannels(num_channels)
    output.setrate(sample_rate)
    output.setformat(aa.PCM_FORMAT_S16_LE)
    output.setperiodsize(CHUNK_SIZE)

    # Output a bit about what we're about to play
    song_filename = os.path.abspath(song_filename)
    logging.info("Playing: " + song_filename + " (" + str(musicfile.getnframes() / sample_rate)
                 + " sec)")

    cache = []
    cache_found = False
    cache_filename = os.path.dirname(song_filename) + "/." + os.path.basename(song_filename) \
        + ".sync.gz"
    # The values 12 and 1.5 are good estimates for first time playing back (i.e. before we have
    # the actual mean and standard deviations calculated for each channel).
    mean = [12.0 for _ in range(hc.GPIOLEN)]
    std = [1.5 for _ in range(hc.GPIOLEN)]
    if args.readcache:
        # Read in cached fft
        try:
            with gzip.open(cache_filename, 'rb') as playlist_fp:
                cachefile = csv.reader(playlist_fp, delimiter=',')
                for row in cachefile:
                    cache.append([0.0 if np.isinf(float(item)) else float(item) for item in row])
                cache_found = True
                # TODO(todd): Optimize this and / or cache it to avoid delay here
                cache_matrix = np.array(cache)
                for i in range(0, hc.GPIOLEN):
                    std[i] = np.std([item for item in cache_matrix[:, i] if item > 0])
                    mean[i] = np.mean([item for item in cache_matrix[:, i] if item > 0])
                logging.debug("std: " + str(std) + ", mean: " + str(mean))
        except IOError:
            logging.warn("Cached sync data song_filename not found: '" + cache_filename
                         + ".  One will be generated.")

    # Process audio song_filename
    row = 0
    data = musicfile.readframes(CHUNK_SIZE)
    frequency_limits = calculate_channel_frequency(_MIN_FREQUENCY,
                                                   _MAX_FREQUENCY,
                                                   _CUSTOM_CHANNEL_MAPPING,
                                                   _CUSTOM_CHANNEL_FREQUENCIES)

    while data != '' and not play_now:
        output.write(data)

        # Control lights with cached timing values if they exist
        matrix = None
        if cache_found and args.readcache:
            if row < len(cache):
                matrix = cache[row]
            else:
                logging.warning("Ran out of cached FFT values, will update the cache.")
                cache_found = False

        if matrix == None:
            # No cache - Compute FFT in this chunk, and cache results
            matrix = calculate_levels(data, sample_rate, frequency_limits)
            cache.append(matrix)

        for i in range(0, hc.GPIOLEN):
            if hc.is_pin_pwm(i):
                # Output pwm, where off is at 0.5 std below the mean
                # and full on is at 0.75 std above the mean.
                brightness = matrix[i] - mean[i] + 0.5 * std[i]
                brightness = brightness / (1.25 * std[i])
                if brightness > 1.0:
                    brightness = 1.0
                if brightness < 0:
                    brightness = 0
                hc.turn_on_light(i, True, int(brightness * 60))
            else:
                if limit[i] < matrix[i] * _LIMIT_THRESHOLD:
                    limit[i] = limit[i] * _LIMIT_THRESHOLD_INCREASE
                    logging.debug("++++ channel: {0}; limit: {1:.3f}".format(i, limit[i]))
                # Amplitude has reached threshold
                if matrix[i] > limit[i]:
                    hc.turn_on_light(i, True)
                    offct[i] = 0
                else:  # Amplitude did not reach threshold
                    offct[i] = offct[i] + 1
                    if offct[i] > _MAX_OFF_CYCLES:
                        offct[i] = 0
                        limit[i] = limit[i] * _LIMIT_THRESHOLD_DECREASE  # old value 0.8
                    logging.debug("---- channel: {0}; limit: {1:.3f}".format(i, limit[i]))
                    hc.turn_off_light(i, True)

        # Read next chunk of data from music song_filename
        data = musicfile.readframes(CHUNK_SIZE)
        row = row + 1

        # Load new application state in case we've been interrupted
        cm.load_state()
        play_now = int(cm.get_state('play_now', 0))

    if not cache_found:
        with gzip.open(cache_filename, 'wb') as playlist_fp:
            writer = csv.writer(playlist_fp, delimiter=',')
            writer.writerows(cache)
            logging.info("Cached sync data written to '." + cache_filename
                         + "' [" + str(len(cache)) + " rows]")

    # We're done, turn it all off ;)
    hc.clean_up()

if __name__ == "__main__":
    main()
