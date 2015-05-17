#!/usr/bin/env python

from netflix import NetflixAPI

API_KEY    = 'TODO: pass on command line'
API_SECRET = 'TODO: pass on command line'
CALLBACK_URL = 'http://api.netflix.com/oauth/request_token'

# OAuth stage 1
auth = NetflixAPI(
    api_key=API_KEY, api_secret=API_SECRET, callback_url=CALLBACK_URL
).get_authentication_tokens()

# OAuth stage 2
auth = NetflixAPI(
    api_key=API_KEY, api_secret=API_SECRET, oauth_token=auth['oauth_token'],
    oauth_token_secret=auth['oauth_token_secret']
).get_auth_tokens(auth['login_url'])

api = NetflixAPI(
    api_key=API_KEY, api_secret=API_SECRET, oauth_token=auth['oauth_token'],
    oauth_token_secret=auth['oauth_token_secret'], user_id=auth['user_id'])

queue = api.get('queues/instant')
print queue

#authorized_tokens = n.get_auth_tokens(oauth_verifier)

#final_oauth_token = authorized_tokens['oauth_token']
#final_oauth_token_secret = authorized_tokens['oauth_token_secret']
#final_user_id = authorized_tokens['user_id']

# Save those tokens and user_id to the database for a later use?
#n = NetflixAPI(api_key = '*your app key*',
#               api_secret = '*your app secret*',
#               oauth_token=final_tokens['oauth_token'],
#               oauth_token_secret=final_tokens['oauth_token_secret'],
#               user_id=final_tokens['user_id'])

# Return a list of the users Instant Queue.
#instant_queue = n.get('queues/instant')
#print instant_queue