# !/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Todd Giles (todd@lightshowpi.com)
# Author: Chris Usey (chris.usey@gmail.com)
# Author: Ryan Jennings
# Author: Paul Dunn (dunnsept@gmail.com)
# Author: Tom Enos
"""
Play any audio file and synchronize lights to the music

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
The values are cached in a npz archive file in the same location as the
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
import argparse
import atexit
import logging
import os
import random
import subprocess
import sys
import wave

import alsaaudio as aa
import decoder
import fft
import hardware_controller as hc
import numpy as np

from prepostshow import PrePostShow

# Configurations
cm = hc.cm
lightshow_config = cm.lightshow()
audio_config = cm.audio_processing()

_MODE = lightshow_config['mode']
_PLAYLIST_PATH = lightshow_config['playlist_path']
_RANDOMIZE_PLAYLIST = lightshow_config['randomize_playlist']

USEFM = audio_config['fm']
if USEFM:
    FM_FREQUENCY = audio_config['frequency']
    play_stereo = True
    music_pipe_r, music_pipe_w = os.pipe()

GPIOLEN = hc.GPIOLEN
CHUNK_SIZE = audio_config['chunk_size']


@atexit.register
def on_exit():
    # We're done, turn it all off and clean up things ;)
    hc.clean_up()


def calculate_channel_frequency():
    """
    Calculate frequency values

    Calculate frequency values for each channel,
    taking into account custom settings.
    """
    min_frequency = audio_config['min_frequency']
    max_frequency = audio_config['max_frequency']
    custom_channel_mapping = audio_config['custom_channel_mapping']
    custom_channel_frequencies = audio_config['custom_channel_frequencies']

    # How many channels do we need to calculate the frequency for
    if custom_channel_mapping != 0 and len(custom_channel_mapping) == GPIOLEN:
        logging.debug("Custom Channel Mapping is being used: %s", str(custom_channel_mapping))
        channel_length = max(custom_channel_mapping)
    else:
        logging.debug("Normal Channel Mapping is being used.")
        channel_length = GPIOLEN

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
        for pin in range(1, GPIOLEN + 1):
            frequency_limits.append(frequency_limits[-1]
                                    * 10 ** (3 / (10 * (1 / octaves_per_channel))))
    for pin in range(0, channel_length):
        frequency_store.append((frequency_limits[pin], frequency_limits[pin + 1]))
        logging.debug("channel %d is %6.2f to %6.2f ", pin, frequency_limits[pin],
                      frequency_limits[pin + 1])

    # we have the frequencies now lets map them if custom mapping is defined
    if custom_channel_mapping != 0 and len(custom_channel_mapping) == GPIOLEN:
        frequency_map = []
        for pin in range(0, GPIOLEN):
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
    """
    Update the state of all the lights

    Update the state of all the lights based upon the current
    frequency response matrix
    :param std: numpy.std()
    :param mean: numpy.mean()
    :param matrix: list of floats
    """
    for pin in range(0, GPIOLEN):
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
    sample_rate = lightshow_config['audio_in_sample_rate']
    input_channels = lightshow_config['audio_in_channels']

    # Open the input stream from default input device
    stream = aa.PCM(aa.PCM_CAPTURE, aa.PCM_NORMAL, lightshow_config['audio_in_card'])
    stream.setchannels(input_channels)
    stream.setformat(aa.PCM_FORMAT_S16_LE)  # Expose in config if needed
    stream.setrate(sample_rate)
    stream.setperiodsize(CHUNK_SIZE)

    logging.debug("Running in audio-in mode - will run until Ctrl+C is pressed")
    print "Running in audio-in mode, use Ctrl+C to stop"
    try:
        hc.initialize()
        frequency_limits = calculate_channel_frequency()

        # Start with these as our initial guesses - will calculate a rolling mean / std 
        # as we get input data.
        mean = [12.0 for _ in range(GPIOLEN)]
        std = [0.5 for _ in range(GPIOLEN)]
        recent_samples = np.empty((250, GPIOLEN))
        num_samples = 0

        # Listen on the audio input device until CTRL-C is pressed
        while True:
            l, data = stream.read()

            if l:
                try:
                    matrix = fft.calculate_levels(data,
                                                  CHUNK_SIZE,
                                                  sample_rate,
                                                  frequency_limits,
                                                  GPIOLEN,
                                                  input_channels)
                    if not np.isfinite(np.sum(matrix)):
                        # Bad data --- skip it
                        continue
                except ValueError as error:
                    # TODO(todd): This is most likely occuring due to extra time in calculating
                    # mean/std every 250 samples which causes more to be read than expected the
                    # next time around.  Would be good to update mean/std in separate thread to
                    # avoid this --- but for now, skip it when we run into this error is good 
                    # enough ;)
                    logging.debug("skipping update: " + str(error))
                    continue

                update_lights(matrix, mean, std)

                # Keep track of the last N samples to compute a running std / mean
                #
                # TODO(todd): Look into using this algorithm to compute this on a per sample basis:
                # http://www.johndcook.com/blog/standard_deviation/                
                if num_samples >= 250:
                    no_connection_ct = 0
                    for i in range(0, GPIOLEN):
                        mean[i] = np.mean([item for item in recent_samples[:, i] if item > 0])
                        std[i] = np.std([item for item in recent_samples[:, i] if item > 0])

                        # Count how many channels are below 10, 
                        # if more than 1/2, assume noise (no connection)
                        if mean[i] < 10.0:
                            no_connection_ct += 1

                    # If more than 1/2 of the channels appear to be not connected, turn all off
                    if no_connection_ct > GPIOLEN / 2:
                        logging.debug("no input detected, turning all lights off")
                        mean = [20 for _ in range(GPIOLEN)]
                    else:
                        logging.debug("std: " + str(std) + ", mean: " + str(mean))
                    num_samples = 0
                else:
                    for i in range(0, GPIOLEN):
                        recent_samples[num_samples][i] = matrix[i]
                    num_samples += 1

    except KeyboardInterrupt:
        pass
    finally:
        print "\nStopping"
        hc.clean_up()


def next_song():
    """
    Get the next song to play from the playlist
    :rtype : String, containing the song filename
    """
    song_to_play = int(cm.get_state('song_to_play', 0))
    play_now = int(cm.get_state('play_now', 0))
    song_filename = args.file

    if args.playlist is not None and args.file is None:
        most_votes = [None, None, []]

        # read playlist from file
        playlist = cm.songs(args.playlist)
        songs = []
        for song in playlist:
            if len(song) < 2 or len(song) > 4:
                logging.warn('Invalid playlist enrty.  Each line should be in the form: '
                             '<song name><tab><path to song>')
                continue
            elif len(song) == 2:
                song.append(set())
            else:
                song[2] = set(song[2].split(','))
                if len(song) == 3 and len(song[2]) >= len(most_votes[2]):
                    most_votes = song
            songs.append(song)

        if most_votes[0] is not None:
            logging.info("Most Votes: " + str(most_votes))
            current_song = most_votes

            for song in songs:
                if current_song == song and len(song) == 3:
                    song.append("playing!")
                if len(song[2]) > 0:
                    song[2] = ",".join(song[2])
                else:
                    del song[2]
            cm.update_songs(args.playlist, songs)
        else:
            # Get a "play now" requested song
            if 0 < play_now <= len(songs):
                current_song = songs[play_now - 1]

            # Get random song
            elif _RANDOMIZE_PLAYLIST:
                # Use python's random.randrange() to get a random song
                current_song = songs[random.randrange(len(songs))]

            # Play next song in the lineup
            else:
                if song_to_play <= len(songs) - 1:
                    song_to_play = song_to_play
                else:
                    song_to_play = 0

                current_song = songs[song_to_play]

                if (song_to_play + 1) <= len(songs) - 1:
                    next_song_to_play = (song_to_play + 1)
                else:
                    next_song_to_play = 0

                cm.update_state('song_to_play', next_song_to_play)

        # Get filename to play and store the current song playing in state cfg
        song_filename = current_song[1]
        cm.update_state('current_song', songs.index(current_song))

    return song_filename.replace("$SYNCHRONIZED_LIGHTS_HOME", cm.HOME_DIR)


def set_up_audio_output(song_filename):
    """
    Set up the audio output device(s)

    :rtype : tuple, tuple of output device(s) and decoder object
    :param song_filename: string, path and name of song file
    """
    if song_filename.endswith('.wav'):
        music_file = wave.open(song_filename, 'r')
    else:
        music_file = decoder.open(song_filename)

    sample_rate = music_file.getframerate()
    num_channels = music_file.getnchannels()

    fm_process = None
    output = None

    if USEFM:
        logging.info("Sending output as fm transmission")

        with open(os.devnull, "w") as dev_null:
            # play_stereo is always True as coded, Should it be changed to
            # an option in the config file?
            fm_process = subprocess.Popen(["sudo",
                                           cm.HOME_DIR + "/bin/pifm",
                                           "-",
                                           str(FM_FREQUENCY),
                                           "44100",
                                           "stereo" if play_stereo else "mono"],
                                          stdin=music_pipe_r,
                                          stdout=dev_null)
    else:
        output = aa.PCM(aa.PCM_PLAYBACK, aa.PCM_NORMAL)
        output.setchannels(num_channels)
        output.setrate(sample_rate)
        output.setformat(aa.PCM_FORMAT_S16_LE)
        output.setperiodsize(CHUNK_SIZE)

    return (fm_process, output), music_file


def save_matrix(cache_filename, cache_matrix, sample_rate, num_channels):
    """
    Save the data necessary for playback so that it will not need to
    be calculated again

    :param cache_filename: string, path and name of sync file
    :param cache_matrix: numpy.array(), fft data for the music file
    :param sample_rate: int, music sample_rate
    :param num_channels: int, number of channels in music file
    """
    show_configuration = np.array([[GPIOLEN],
                                   [sample_rate],
                                   [audio_config['min_frequency']],
                                   [audio_config['max_frequency']],
                                   [audio_config['custom_channel_mapping']],
                                   [audio_config['custom_channel_frequencies']],
                                   [CHUNK_SIZE],
                                   [num_channels]], dtype=object)

    # Compute the standard deviation and mean values for the cache
    mean = [0 for _ in range(GPIOLEN)]
    std = [0 for _ in range(GPIOLEN)]
    for i in range(0, GPIOLEN):
        std[i] = np.std([item for item in cache_matrix[:, i] if item > 0])
        mean[i] = np.mean([item for item in cache_matrix[:, i] if item > 0])

    # Save the cache using numpy savez
    np.savez(cache_filename,
             cache_matrix=cache_matrix,
             mean=mean,
             std=std,
             cached_configuration=show_configuration)

    logging.info("Cached sync data written to '." + cache_filename
                 + "' [" + str(len(cache_matrix)) + " rows]")


def create_cache(items):
    """
    Create sync file(s) for a single file or a playlist

    :param items: string or list of strings, a playlist or filename
    """
    cache_matrix = np.empty(shape=[0, GPIOLEN])
    mean = [0.0 for _ in range(GPIOLEN)]
    std = [0.0 for _ in range(GPIOLEN)]

    a_types = [".mp3", ".mp4", ".m4a", ".m4b", ".aac", ".ogg", ".flac", ".wma", ".wav"]

    if os.path.splitext(os.path.basename(items))[1] in a_types:
        playlist = [items]
    else:
        playlist = list()
        with open(items, 'r') as playlist_items:
            for line in playlist_items:
                try:
                    temp = line.strip().split('\t')[1]
                    if os.path.isfile(temp):
                        playlist.append(temp)
                except IOError:
                    pass

    for song in playlist:
        #print "Generating sync file for :", song
        logging.info("Generating sync file for :" + song)
        per_song_config_filename = song + ".cfg"
        per_song_config(per_song_config_filename)

        if song.endswith('.wav'):
            music_file = wave.open(song, 'r')
        else:
            music_file = decoder.open(song)

        cache_filename = os.path.dirname(song) + "/." + os.path.basename(song) + ".sync.npz"
        cache_matrix = playback(music_file, cache_matrix, std, mean, False, (None, None), song)
        sample_rate = music_file.getframerate()
        num_channels = music_file.getnchannels()

        save_matrix(cache_filename, cache_matrix, sample_rate, num_channels)

        sys.stdout.write("\rSync file generated for  :%s %d%%" % (song, 100))
        sys.stdout.write("\n")
        sys.stdout.flush()
        #print "Sync file generated for :", song
        logging.info("Sync file generated for :" + song)


def read_cache(cache_filename, music_file):
    """
    Read sync file and validate cached data matches the loaded
    configuration

    :rtype : tuple of objects,
             boolean, valid cache data found
             numpy.std(), standard deviation of the fft data
             numpy.mean(), mean of the fft data
             numpy.array(), fft data  for the audio file
    :param cache_filename: string, path and filename of cached data
    :param music_file: decoder object, audio file
    """
    cache_found = False

    sample_rate = music_file.getframerate()
    num_channels = music_file.getnchannels()

    # create empty array for the cache_matrix
    cache_matrix = np.empty(shape=[0, GPIOLEN])

    # The values 12 and 1.5 are good estimates for first time playing back 
    # (i.e. before we have the actual mean and standard deviations 
    # calculated for each channel).
    mean = [12.0 for _ in range(GPIOLEN)]
    std = [1.5 for _ in range(GPIOLEN)]

    try:
        # load cache from file
        cache_arrays = np.load(cache_filename)

        # get the current configuration to compare to
        # what is stored in the cached array
        # index 7 holds -1, reserved for future use
        show_configuration = np.array([[GPIOLEN],
                                       [sample_rate],
                                       [audio_config['min_frequency']],
                                       [audio_config['max_frequency']],
                                       [audio_config['custom_channel_mapping']],
                                       [audio_config['custom_channel_frequencies']],
                                       [CHUNK_SIZE],
                                       [num_channels]], dtype=object)

        # cached hardware configuration from sync file
        cached_configuration = cache_arrays["cached_configuration"]

        # Compare current config to cached config
        if (show_configuration == cached_configuration).all():
            cache_found = True
            std = cache_arrays["std"]
            mean = cache_arrays["mean"]
            cache_matrix = cache_arrays["cache_matrix"]

        if cache_found:
            logging.debug("std: " + str(std) + ", mean: " + str(mean))
        else:
            logging.warn('Cached configuration does not match current configuration.  '
                         'Generating new cache file with current show configuration')
    except IOError:
        logging.warn("Cached sync data song_filename not found: '"
                     + cache_filename
                     + ".  One will be generated.")

    return cache_found, std, mean, cache_matrix


def playback(music_file, cache_matrix, std, mean, cache_found, output_device, song=None):
    # Process audio song_filename
    """
    Playback the audio and trigger the lights

    :param cache_matrix: numpy.array(), fft data for the audio file
    :param std: numpy.std(), standard deviation of the fft data
    :param mean: numpy.mean(), mean of the fft data
    :param music_file: decoder object, audio file
    :param cache_found: boolean, was a valid sync file found
    :param output_device: tuple, (alsaaudio device data or None, fm process or None)
    :return: numpy.array(), fft data for the audio file
    """
    play_now = int(cm.get_state('play_now', 0))
    fm_process = output_device[0]
    output = output_device[1]
    sample_rate = music_file.getframerate()

    row = 0
    data = music_file.readframes(CHUNK_SIZE)
    frequency_limits = calculate_channel_frequency()
    total_frames = music_file.getnframes() / 100
    counter = 0
    percentage = 0

    while data != '' and not play_now:
        if fm_process:
            os.write(music_pipe_w, data)
        if output:
            output.write(data)

        # Control lights with cached timing values if they exist
        matrix = None
        if cache_found and args.readcache:
            if row < len(cache_matrix):
                matrix = cache_matrix[row].tolist()
            else:
                logging.warning("Ran out of cached FFT values, will update the cache.")
                cache_found = False

        if matrix is None:
            # No cache - Compute FFT in this chunk, and cache results
            matrix = fft.calculate_levels(data,
                                          CHUNK_SIZE,
                                          sample_rate,
                                          frequency_limits,
                                          GPIOLEN)

            # Add the matrix to the end of the cache 
            cache_matrix = np.vstack([cache_matrix, matrix])

        if not args.createcache:
            update_lights(matrix, mean, std)

        # Read next chunk of data from music song_filename
        data = music_file.readframes(CHUNK_SIZE)
        row += 1

        # Load new application state in case we've been interrupted
        if not args.createcache:
            cm.load_state()
            play_now = int(cm.get_state('play_now', 0))
        else:
            if counter > total_frames:
                percentage += 1
                counter = 0
            counter += CHUNK_SIZE
            sys.stdout.write("\rGenerating sync file for :%s %d%%" % (song, percentage))
            sys.stdout.flush()

    return cache_matrix


def per_song_config(per_song_config_filename):
    """
    Load the configuration for the audio file if it exists
    set variables for playback hear and in the hardware_manager

    :param per_song_config_filename: string, path and filename
    """
    # Get configuration for song playback
    global lightshow_config, audio_config
    if os.path.isfile(per_song_config_filename):
        logging.info("loading custom configuration for " + per_song_config_filename)
        cm.per_song_config(per_song_config_filename)
        lightshow_config = cm.lightshow()
        audio_config = cm.audio_processing()
        hc.load_config()


def play_song():
    """
    Play the next song from the play list (or --file argument).
    """
    play_now = int(cm.get_state('play_now', 0))

    cache_found = False

    std = list()
    mean = list()
    for _ in range(GPIOLEN):
        std.append(0.0)
        mean.append(0.0)
    cache_matrix = np.empty(shape=[0, GPIOLEN])

    # Initialize Lights
    hc.initialize()

    # Handle the pre/post show
    if not play_now:
        result = PrePostShow('preshow', hc).execute()
        if result == PrePostShow.play_now_interrupt:
            play_now = int(cm.get_state('play_now', 0))

    # Determine the next file to play
    song_filename = next_song()

    # Ensure play_now is reset before beginning playback
    if play_now:
        cm.update_state('play_now', 0)

    # Set up audio from file

    # set audio playback device
    output_device, music_file = set_up_audio_output(song_filename)

    sample_rate = music_file.getframerate()
    num_channels = music_file.getnchannels()

    # Output a bit about what we're about to play to the logs
    song_filename = os.path.abspath(song_filename)
    logging.info(
        "Playing: " + song_filename + " (" + str(music_file.getnframes() / sample_rate) + " sec)")

    # Get configuration for song playback
    per_song_config_filename = song_filename + ".cfg"
    per_song_config(per_song_config_filename)

    # Cached data filename
    cache_filename = os.path.dirname(song_filename) + "/." + os.path.basename(
        song_filename) + ".sync.npz"

    # Read in cached fft data if it exists
    if args.readcache:
        cache_found, std, mean, cache_matrix = read_cache(cache_filename, music_file)

    # Process audio song_filename and playback
    cache_matrix = playback(music_file, cache_matrix, std, mean, cache_found, output_device)

    # save the sync file if needed
    if not cache_found:
        # Save the cache matrix, std, mean and the show_configuration variables
        # that matter in the fft calculation to a sync file for future playback
        save_matrix(cache_filename, cache_matrix, sample_rate, num_channels)

    # Cleanup the pifm process
    if USEFM:
        fm_process = output_device[0]
        fm_process.kill()

    # check for postshow
    PrePostShow('postshow', hc).execute()


if __name__ == "__main__":
    # parse command line arguments
    parser = argparse.ArgumentParser()
    filegroup = parser.add_mutually_exclusive_group()
    filegroup.add_argument('--playlist', default=_PLAYLIST_PATH,
                           help='Playlist to choose song from.')
    filegroup.add_argument('--file', help='path to the song to play (required if no'
                                          'playlist is designated)')
    cachegroup = parser.add_mutually_exclusive_group()
    cachegroup.add_argument('--readcache', type=bool, default=True,
                            help='read light timing from cache if available. Default: true')
    cachegroup.add_argument('--createcache', action="store_true",
                            help='create light timing cache without audio playback or lightshow.')
    parser.add_argument('--log', default='DEBUG',
                        help='Set the logging level. levels:INFO, DEBUG, WARNING, ERROR, CRITICAL')

    if parser.parse_args().createcache:
        parser.set_defaults(readcache=False)

    args = parser.parse_args()

    # Make sure one of --playlist or --file was specified
    if args.file is None and args.playlist is None:
        print "One of --playlist or --file must be specified"
        sys.exit()

    # Log to our log file at the specified level
    levels = {'DEBUG': logging.DEBUG,
              'INFO': logging.INFO,
              'WARNING': logging.WARNING,
              'ERROR': logging.ERROR,
              'CRITICAL': logging.CRITICAL}

    level = levels.get(args.log.upper())
    logging.basicConfig(filename=cm.LOG_DIR + '/music_and_lights.play.dbg',
                        format='[%(asctime)s] %(levelname)s {%(pathname)s:%(lineno)d}'
                               ' - %(message)s',
                        level=level)

    # Check if we are generating sync file(s) or playing a show
    if args.createcache:
        create_cache(args.file or args.playlist)
        sys.exit(0)

    # Begin audio playback
    if _MODE == 'audio-in':
        audio_in()
    else:
        play_song()
