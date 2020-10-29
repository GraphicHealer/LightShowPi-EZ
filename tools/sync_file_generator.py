# sync file generator for lightshowpi
# run usage
#
# python3 sync_file_generator.py
#
# Enter y to confirm that you wish to run this
# Enter the path to the folder containing your audio files
# along with the sync files it will also generate a playlist file
# enter the path to this playlist file in your overrides.cfg and 
# lightshowpi will use this as your new playlist

import decoder
import glob
import mutagen
import numpy as np
import os
import sys
import wave

HOME_DIR = os.getenv("SYNCHRONIZED_LIGHTS_HOME")
if not HOME_DIR:
    print("Need to setup SYNCHRONIZED_LIGHTS_HOME environment variable, "
          "see readme")
    sys.exit()

# hack to get the configuration_manager and fft modules to load
# from a different directory
path = list(sys.path)

# insert script location and configuration_manager location into path
sys.path.insert(0, HOME_DIR + "/py")

# import the configuration_manager and fft now that we can
import fft

import hardware_controller

hc = hardware_controller.Hardware()

# get copy of configuration manager
cm = hc.cm

#### reusing code from synchronized_lights.py
#### no need to reinvent the wheel

GPIOLEN = cm.hardware.gpio_len 
_MIN_FREQUENCY = cm.audio_processing.min_frequency
_MAX_FREQUENCY = cm.audio_processing.max_frequency

try:
    _CUSTOM_CHANNEL_MAPPING = cm.audio_processing.custom_channel_mapping
except:
    _CUSTOM_CHANNEL_MAPPING = 0

try:
    _CUSTOM_CHANNEL_FREQUENCIES = cm.audio_processing.custom_channel_frequencies
except:
    _CUSTOM_CHANNEL_FREQUENCIES = 0

CHUNK_SIZE = 2048  # Use a multiple of 8 (move this to config)

def calculate_channel_frequency(min_frequency,
                                max_frequency,
                                custom_channel_mapping,
                                custom_channel_frequencies):
    """
    Calculate frequency values

    Calculate frequency values for each channel,
    taking into account custom settings.
    """

    # How many channels do we need to calculate the frequency for
    if custom_channel_mapping != 0 and len(custom_channel_mapping) == GPIOLEN:
        channel_length = max(custom_channel_mapping)
    else:
        channel_length = GPIOLEN

    octaves = (np.log(max_frequency / min_frequency)) / np.log(2)
    octaves_per_channel = octaves / channel_length
    frequency_limits = []
    frequency_store = []

    frequency_limits.append(min_frequency)
    if custom_channel_frequencies != 0 and (len(custom_channel_frequencies)
                                            >= channel_length + 1):
        frequency_limits = custom_channel_frequencies
    else:
        for i in range(1, GPIOLEN + 1):
            frequency_limits.append(frequency_limits[-1]
                                    * 10 ** (3 /
                                             (10 * (1 / octaves_per_channel))))
    for i in range(0, channel_length):
        frequency_store.append((frequency_limits[i], frequency_limits[i + 1]))

    # we have the frequencies now lets map them if custom mapping is defined
    if custom_channel_mapping != 0 and len(custom_channel_mapping) == GPIOLEN:
        frequency_map = []
        for i in range(0, GPIOLEN):
            mapped_channel = custom_channel_mapping[i] - 1
            mapped_frequency_set = frequency_store[mapped_channel]
            mapped_frequency_set_low = mapped_frequency_set[0]
            mapped_frequency_set_high = mapped_frequency_set[1]
            frequency_map.append(mapped_frequency_set)
        return frequency_map
    else:
        return frequency_store

def cache_song(song_filename):
    """Play the next song from the play list (or --file argument)."""
    # Initialize FFT stats
    matrix = [0 for _ in range(GPIOLEN)] # get length of gpio and assign it to a variable

    # Set up audio
    if song_filename.endswith('.wav'):
        musicfile = wave.open(song_filename, 'r')
    else:
        musicfile = decoder.open(song_filename)

    sample_rate = musicfile.getframerate()
    num_channels = musicfile.getnchannels()

    fft_calc = fft.FFT(CHUNK_SIZE,
                       sample_rate,
                       GPIOLEN,
                       _MIN_FREQUENCY,
                       _MAX_FREQUENCY,
                       _CUSTOM_CHANNEL_MAPPING,
                       _CUSTOM_CHANNEL_FREQUENCIES)

    song_filename = os.path.abspath(song_filename)

    # create empty array for the cache_matrix
    cache_matrix = np.empty(shape=[0, GPIOLEN])
    cache_filename = \
        os.path.dirname(song_filename) + "/." + os.path.basename(song_filename) + ".sync"

    # The values 12 and 1.5 are good estimates for first time playing back 
    # (i.e. before we have the actual mean and standard deviations 
    # calculated for each channel).
    mean = [12.0 for _ in range(GPIOLEN)]
    std = [1.5 for _ in range(GPIOLEN)]

    # Process audio song_filename
    row = 0
    data = musicfile.readframes(CHUNK_SIZE) # move chunk_size to configuration_manager

    while data != b'':
        # No cache - Compute FFT in this chunk, and cache results
        matrix = fft_calc.calculate_levels(data)

        # Add the matrix to the end of the cache 
        cache_matrix = np.vstack([cache_matrix, matrix])

        # Read next chunk of data from music song_filename
        data = musicfile.readframes(CHUNK_SIZE)
        row = row + 1

    # Compute the standard deviation and mean values for the cache
    for i in range(0, GPIOLEN):
        std[i] = np.std([item for item in cache_matrix[:, i] if item > 0])
        mean[i] = np.mean([item for item in cache_matrix[:, i] if item > 0])

    # Add mean and std to the top of the cache
    cache_matrix = np.vstack([mean, cache_matrix])
    cache_matrix = np.vstack([std, cache_matrix])

    # Save the cache using numpy savetxt
    np.savetxt(cache_filename, cache_matrix)

#### end reuse 

def main():        
    print ("Do you want to generate sync files?")
    print 
    print ("This could take a while if you have a lot of songs")

    question = input("Would you like to proceed? (Y to continue) :")

    if not question in ["y", "Y"]:
        sys.exit(0)

    location = input("Enter the path to the folder of songs:")
    location += "/"

    sync_list = list()
    audio_file_types = ["*.mp3", "*.mp4",
                        "*.m4a", "*.m4b",
                        "*.aac", "*.ogg",
                        "*.flac", "*.oga",
                        "*.wma", "*.wav"]

    for file_type in audio_file_types:
        sync_list.extend(glob.glob(location + file_type))

    playlistFile = open(location + "playlist", "w")

    for song in sync_list:
        print ("Generating sync file for",song)
        cache_song(song)
        print ("cached")

        metadata = mutagen.File(song, easy=True)
        if "title" in metadata:
            title = metadata["title"][0]
        else:
            title = os.path.splitext(os.path.basename(song))[0].strip()
            title = title.replace("_", " ")
            title = title.replace("-", " - ")
        playlistFile.write(title + "\t" + song + "\n")

    playlistFile.close()

    print ("All Finished.")
    print ("A playlist was also generated")
    print (location + "playlist")
    sys.path[:] = path

if __name__ == "__main__":
    main()
