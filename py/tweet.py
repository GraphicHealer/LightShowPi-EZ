"""Use Twitter to show current song playing

Author : Brett Reinhard

To setup automated tweeting, you will need a twitter account with a verified phone number.
Go to the apps.twitter.com, login to your twitter account. 
Create a new app with the following information: 
 Name (of the app)
 Description
 A url in http(s)://domain.com 
Agree to the terms. 
Click on the Keys and Access Tokens tab
Consumer Key, and Consumer Secret Key are automatically generated. 
Under 'Your Access Token', select generate access tokens. 
This will generate Access Token, and Access Token Secret.
You now have access to your newly generated Access Token, and Access Token Secret.
Fill the tokens (KEYS) and secrets in the locations below where 'USER INPUTS DATA' 
CONSUMER_KEY = 'consumer_token' 
CONSUMER_SECRET = 'consumer_token_secret' 
ACCESS_KEY = 'access_token' 
ACCESS_SECRET = 'access_token_secret'

Ensure that the keys are enclosed by single quotes.


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
