# !/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Todd Giles (todd@lightshowpi.com)
"""
FFT methods for computing / analyzing frequency response of audio.

These are simply wrappers around FFT support of numpy.

Third party dependencies:

numpy: for FFT calculation - http://www.numpy.org/
"""
import sys

import numpy as np


def calculate_levels(data, chunk_size, sample_rate, frequency_limits, gpiolen, channels=2):
    """
    Calculate frequency response for each channel defined in frequency_limits

    :rtype : numpy.array(), frequency limits for channels
    :param data: decoder.frames(), audio data for fft calculations
    :param chunk_size: int, chunk size of audio data
    :param sample_rate: int, audio file sample rate
    :param frequency_limits: list, list of frequency_limits
    :param gpiolen: int, length of gpio to process
    :param channels: int, number of audio channels to process for

    Initial FFT code inspired from the code posted here:
    http://www.raspberrypi.org/phpBB3/viewtopic.php?t=35838&p=454041

    Optimizations from work by Scott Driscoll:
    http://www.instructables.com/id/Raspberry-Pi-Spectrum-Analyzer-with-RGB-LED-Strip-/
    """

    # create a numpy array, taking just the left channel if stereo
    data_stereo = np.frombuffer(data, dtype=np.int16)
    if channels == 2:
        # data has 2 bytes per channel
        data = np.empty(len(data) / (2 * channels))

        # pull out the even values, just using left channel
        data[:] = data_stereo[::2]
    elif channels == 1:
        data = data_stereo

    # if you take an FFT of a chunk of audio, the edges will look like
    # super high frequency cutoffs. Applying a window tapers the edges
    # of each end of the chunk down to zero.
    window = np.hanning(len(data))
    data = data * window

    # Apply FFT - real data
    fourier = np.fft.rfft(data)

    # Remove last element in array to make it the same size as chunk_size
    fourier = np.delete(fourier, len(fourier) - 1)

    # Calculate the power spectrum
    power = np.abs(fourier) ** 2

    matrix = np.zeros(gpiolen, dtype='float64')
    for pin in range(gpiolen):
        # take the log10 of the resulting sum to approximate how human ears 
        # perceive sound levels
        
        # Get the power array index corresponding to a particular frequency.
        idx1 = int(chunk_size * frequency_limits[pin][0] / sample_rate)
        idx2 = int(chunk_size * frequency_limits[pin][1] / sample_rate)
        
        # if index1 is the same as index2 the value is an invalid value
        # we can fix this by incrementing index2 by 1, This is a tempoary fix
        # for RuntimeWarning: invalid value encountered in double_scalars
        # generated while calculating the standard deviation.  This warning
        # results in some channels not lighting up during playback.
        if idx1 == idx2:
            idx2 += 1
        
        npsum = np.sum(power[idx1:idx2:1])
        
        # if the sum is 0 lets not take log10, just use 0
        if npsum == 0:
            matrix[pin] = 0
        else:
            matrix[pin] = np.log10(npsum)

    return matrix
