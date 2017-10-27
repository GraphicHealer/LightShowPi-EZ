#!/usr/bin/env python
#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.org/
#
# Author: Tom Enos
#

"""Compute a running mean and standard deviation

Receives an numpy array of fft data from lightshowpi and computes a
running mean and standard deviation for each element in the array

derived from the work of John D. Cook
http://www.johndcook.com/blog/standard_deviation/

Third party dependencies:

numpy: for calculation
    http://www.numpy.org/
"""

from numpy import *


class Stats(object):
    def __init__(self, length):
        """Constructor
        
        :param length: the length of the matrix
        :type length: int
        """
        self.length = length
        self.clear()
        self.sample_count = 0
        self.old_mean = zeros(length, dtype='float32')
        self.old_std = zeros(length, dtype='float32')
        self.new_mean = zeros(length, dtype='float32')
        self.new_std = zeros(length, dtype='float32')

    def clear(self):
        self.sample_count = 0
        self.old_mean = zeros(self.length, dtype='float32')
        self.old_std = zeros(self.length, dtype='float32')
        self.new_mean = zeros(self.length, dtype='float32')
        self.new_std = zeros(self.length, dtype='float32')

    def preload(self, mean_value, std_value, sample_count=2):
        """Add a starting samples to the running standard deviation and mean_value
        
        This data does not need to be accurate.  It is only a base starting
        point for our light show.  With out preloading some values the show 
        will start with all lights on and then slowly change to what we want
        to see.  
        
        :param mean_value: new sample mean_value starting point
        :type mean_value: numpy array
        :param std_value: new sample standard deviation starting point
        :type std_value: numpy array
        :param sample_count: how many samples to start with (min 2)
        :type sample_count: int
        """
        if len(mean_value) == self.length and len(
                std_value) == self.length and sample_count > 1 and self.sample_count == 0:
            # cast all arrays to numpy just to make sure the data type is correct
            self.new_mean = array(mean_value, dtype='float32')
            self.new_std = array(std_value, dtype='float32')
            self.old_mean = array(mean_value, dtype='float32')
            self.old_std = array(std_value, dtype='float32')
            self.sample_count = sample_count

    def push(self, data):
        """Add a new sample to the running standard deviation and mean

        data should be numpy array the same length as self.length
        :param data: new sample data, this must be a numpy array 
        :type data: numpy array
        """
        self.sample_count += 1

        if self.sample_count == 1:
            self.old_mean = self.new_mean
            self.new_mean = data
            self.old_std = zeros(length, dtype='float32')
        else:
            self.new_mean = self.old_mean + (data - self.old_mean) / self.sample_count
            self.new_std = self.old_std + (data - self.old_mean) * (data - self.new_mean)

            # set up for next iteration
            self.old_mean = self.new_mean
            self.old_std = self.new_std

    def num_data_values(self):
        """Get the current number of observations in the sample
        
        :return: current samples observed
        :rtype: int
        """
        return self.sample_count

    def mean(self):
        """Get the current mean
        
        :return: current sampled mean
        :rtype: numpy array
        """
        return self.new_mean

    def variance(self):
        """Get the current variance 
        
        :return: current variance
        :rtype: numpy array
        """
        if self.sample_count > 1:
            return self.new_std / (self.sample_count - 1.0)
        else:
            return zeros(length, dtype='float32')

    def std(self):
        """Get the current standard deviation 
        
        :return: current standard deviation
        :rtype: numpy array
        """
        return sqrt(self.variance())
