# -*- coding: utf-8 -*-
import os, sys, json, tweepy
import requests, datetime, radar, random
from tweepy import StreamListener
from tweepy import Stream
from pymongo import MongoClient

CONSUMER_KEY = None
CONSUMER_SECRET = None
ACCESS_KEY = None
ACCESS_SECRET = None
MONGO_URI = None
WH_LOGS_SOURCE = None

try:
    pathname = os.path.dirname(sys.argv[0])
    config_file = os.path.abspath(pathname)+'/config.json'
    with open(config_file) as data_file:
        data = json.load(data_file)
    # Creds
    CONSUMER_KEY = data['CONSUMER_KEY']
    CONSUMER_SECRET = data['CONSUMER_SECRET']
    ACCESS_KEY = data['ACCESS_KEY']
    ACCESS_SECRET = data['ACCESS_SECRET']
    MONGO_URI = data['MONGO_URI']
    TWITTER_TARGETS = data['TWITTER_TARGETS']
    RESPONSE_TARGETS = data['RESPONSE_TARGETS']
    WH_LOGS_SOURCE = data['WH_LOGS_SOURCE']

except IOError as err:
    print "[error] "+err.message

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth)

# get_older_status('<twitter_handle>')
s_date = datetime.date(2017,01,20)
e_date = datetime.datetime.now().date()

class StreamListener(tweepy.StreamListener):
    '''
    Twitter Stream listener
    '''
    def has_tweet(self, tid):
        '''
        Checks if a tweet already exists in the db
        '''
        client = MongoClient(MONGO_URI)
        db = client['djt']
        tweets = db.tweets
        twt = tweets.find({'tid':tid, 'processed':True})
        if twt.count()>0:
            return True
        else:
            return False

    def get_log(self):
        '''
        Retrieves an unprocessed log from the db
        '''
        client = MongoClient(MONGO_URI)
        db = client['casablanca']
        docs = db.wh_logs.find({'place':'White House', 'processed':False}).sort('date', 1).limit(1)
        log = None
        for doc in docs:
            log = doc
        v_date = log['date'].strftime('%b %d, %Y')
        v = log['visitor']
        vname = v['first_name']+' '+v['last_name']
        title = v['title'] if v['title'] else ''
        org = v['organization']['name'] if v['organization'] else ''
        msg = '{0} {1} {2} {3} visited the White House'.format(v_date, vname.encode('utf-8'), title.encode('utf-8'), org.encode('utf-8'))
        msg = ' '.join(msg.split())
        log = {'_id':log['_id'], 'message':msg}
        return log

    def update_log_processed(self, objID):
        '''
        Update a log as processed
        '''
        client = MongoClient(MONGO_URI)
        db = client['casablanca']
        log = db.wh_logs.find_one_and_update({'_id':objID}, {'$set':{'processed':True}})
        print "Log Processed: {0}".format(log['_id'])

    def on_status(self, status):
        status_id = status.id_str
        user_id = status.user.id_str
        scr_name = status.user.screen_name
        if (user_id in RESPONSE_TARGETS) and not hasattr(status, 'retweeted_status'):
            log = self.get_log()
            resp_msg = '@{0} '.format(scr_name)+log['message']
            resp_msg = ' '.join(resp_msg.split())
            tweet = ' '.join(log['message'].split())

            # reply to reponse targets
            api.update_status(status=resp_msg, in_reply_to_status_id=status_id)

            # just plain ole tweet to account
            api.update_status(status=tweet)

            # Flag log as processed
            self.update_log_processed(log['_id'])

    def on_error(self, status_code):
        if status_code == 420:
            # print "Error: 420"
            return False

if __name__ == '__main__':
    listener = StreamListener()
    twitterStream = Stream(auth, listener)
    twitterStream.filter(follow=TWITTER_TARGETS)
