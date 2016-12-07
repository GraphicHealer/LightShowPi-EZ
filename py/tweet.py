"""Use Twitter to show current song playing

Author : Brett Reinhard

<Instructions for obtaining KEYs and SECRETs>

"""

import sys
import emoji
import time
from twython import Twython
CONSUMER_KEY = 'USER INPUTS DATA'
CONSUMER_SECRET = 'USER INPUTS DATA'
ACCESS_KEY = 'USER INPUTS DATA'
ACCESS_SECRET = 'USER INPUTS DATA'

currenttime = time.strftime("%I:%M:%S")
api = Twython(CONSUMER_KEY,CONSUMER_SECRET,ACCESS_KEY,ACCESS_SECRET) 
strin = sys.argv[1]
api.update_status(status=emoji.emojize(':christmas_tree:') + emoji.emojize(":gift:",use_aliases=True) + strin + emoji.emojize(':christmas_tree:') +  emoji.emojize(':bell:') + " Updated: " + currenttime + emoji.emojize(':bell:'))
