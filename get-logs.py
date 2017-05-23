# -*- coding: utf-8 -*-
import os, sys, json, tweepy, requests, datetime, radar, random
from tweepy import StreamListener
from tweepy import Stream
from pymongo import MongoClient
from bson import ObjectId

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
    WH_LOGS_SOURCE = data['WH_LOGS_SOURCE']

except IOError as err:
    print "[error] "+err.message

tid = ''
uid = ''
sc = ''
maxid = ''

AUTH = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
AUTH.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(AUTH)

def has_tweet(tid):
    client = MongoClient(MONGO_URI)
    db = client['djt']
    tweets = db.tweets
    twt = tweets.find({'tid':tid,'processed':True})
    if twt.count()>0:
        return True
    else:
        return False

def get_tweet(uid):
    client = MongoClient(MONGO_URI)
    db = client['djt']
    tweets = db.tweets
    twt = tweets.find({'processed':False,'uid':uid}).sort('created_at',1).limit(1)
    status_id=''
    for t in twt:
        status_id = t['tid']
    return status_id

def save_tweet(status):
    client = MongoClient(MONGO_URI)
    db = client['djt']
    tweets = db.tweets
    user_id = status.user.id_str
    screen_name = status.user.screen_name
    tweet_id = status.id_str
    created_at = status.created_at
    reply_id = status.in_reply_to_status_id_str if status.in_reply_to_status_id_str else ''
    reply_name = status.in_reply_to_screen_name if status.in_reply_to_screen_name else ''
    tweet_text = status.text.encode('utf-8')
    processed = False
    twt = tweets.insert({'tid':tweet_id, 'uid':user_id, 'screen_name':screen_name, \
            'reply_to_id':reply_id, 'reply_name':reply_name, 'text':tweet_text, 'created_at':created_at, \
            'processed':processed} )
    msg = "TID: {0}  UID: {1} Handle: {2} RepToID: {3} RepToName: {4} created_at: {5}"
    print msg.format(tweet_id, user_id, screen_name, reply_id, reply_name, created_at)    

def get_older_status_maxid(sn,max_id):
    stuff = api.user_timeline(screen_name = sn, max_id = max_id, count = 200, include_rts = False)
    for s in stuff:
        save_tweet(s)

def get_older_status(sn):
    stuff = api.user_timeline(screen_name = sn, count = 50, include_rts = False)
    for s in stuff:
        save_tweet(s)

def percent_response(screen_name, percentage, followers, status_url):
    emoji = u"\U0001F447"
    MSG = '@{0}\n{1} of your {2} Followers Liked this Tweet:\n'.format(screen_name, percentage, followers) \
        + u"\U0001F447" + '\n{0}'.format(status_url)
    return MSG

def save_src_wh_logs(start_date, end_date):
    '''
    Captures all WH logs withina date range then saves to mongodb
    '''
    client = MongoClient(MONGO_URI)
    db = client['casablanca']
    d = start_date
    delta = datetime.timedelta(days=1)
    while d <= end_date:
        wh_uri = WH_LOGS_SOURCE+d.strftime('%Y-%m-%d')+'.json'
        try:
            response = requests.get(wh_uri)
            response.raise_for_status()
            docs = db.wh_logs.insert_many(response.json()).inserted_ids
            for doc in docs:
                log = db.wh_logs.find_one({'_id':doc})
                str_date = datetime.datetime.strptime(log['date'],'%Y-%m-%d')
                upt_log = db.wh_logs.find_one_and_update({'_id':doc}, {'$set':{'date':str_date,'processed':False}}, upsert=True)
                print upt_log
        except requests.exceptions.HTTPError as err:
            pass
        d += delta

def save_current_src_wh_logs():
    '''
    Captures all WH logs from the last date in mongodb until current date then saves
    new reords to mongodb
    '''
    um = 0
    client = MongoClient(MONGO_URI)
    db = client['casablanca']
    last_date = db.wh_logs.find({}).sort('date',-1).limit(1)
    for d in last_date: 
        s_date = d['date'].date()
    delta = datetime.timedelta(days=1)
    # Plus the date one
    s_date += delta
    print 'Capture Start Date: {0}'.format(s_date.strftime('%Y-%m-%d'))
    e_date = datetime.datetime.now().date()
    
    while s_date <= e_date:
        wh_uri = WH_LOGS_SOURCE+s_date.strftime('%Y-%m-%d')+'.json'
        try:
            response = requests.get(wh_uri)
            response.raise_for_status()
            docs = db.wh_logs.insert_many(response.json()).inserted_ids
            for doc in docs:
                log = db.wh_logs.find_one({'_id':doc})
                str_date = datetime.datetime.strptime(log['date'],'%Y-%m-%d')
                upt_log = db.wh_logs.find_one_and_update({'_id':doc}, {'$set':{'date':str_date,'processed':False}}, upsert=True)
                um += 1
        except requests.exceptions.HTTPError as err:
            pass
        s_date += delta

    print 'Total White Logs Captured: {0}'.format(um)


def get_src_wh_logs(start_date, end_date):
    d = start_date
    delta = datetime.timedelta(days=1)
    while d <= end_date:
        wh_uri = WH_LOGS_SOURCE+d.strftime('%Y-%m-%d')+'.json'
        try:
            print wh_uri
            response = requests.get(wh_uri)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            pass
        d += delta

def get_random_visitor(start_date, end_date):
    d = start_date
    random_date = radar.random_date(start=start_date, stop=end_date)
    wh_uri = WH_LOGS_SOURCE+random_date.strftime('%Y-%m-%d')+'.json'
    vistors = None
    try:
        response = requests.get(wh_uri)
        response.raise_for_status()

        # rv = random.sample(response.json(),len(response.json()))
        rv_json = random.choice(response.json())
        if rv_json['place'] != 'White House':
            get_random_visitor(start_date,end_date)
        else:
            # get the date
            rvdate = datetime.datetime.strptime(rv_json['date'],'%Y-%m-%d')
            v_date = rvdate.strftime('%b %d, %Y')
            v = rv_json['visitor']
            vname = v['first_name']+' '+v['last_name']
            title = v['title'] if v['title'] else ''
            org = v['organization']['name'] if v['organization'] else ''

            txt = 'On '+v_date+' '+vname+' '+title+' '+org+' visited the White House'
            print txt
            print(len(txt))
            return ' '.join(txt.split())
          
    except requests.exceptions.HTTPError as err:
        get_random_visitor(start_date,end_date)


def get_log():
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
    print type(org)

    msg = '{0} {1} {2} {3} visited the White House'.format(v_date, vname.encode('utf-8'), title.encode('utf-8'), org.encode('utf-8'))
    msg = ' '.join(msg.split())
    
    # Check Message Characters
    if len(msg) > 140:
        msg = '{0} {1} {2} visited the White House'.format(v_date, vname.encode('utf-8'), title.encode('utf-8'))
        msg = ' '.join(msg.split())
    log = {'_id':log['_id'], 'message':msg}
    return log

# s_date = datetime.date(2017,01,20)
# e_date = datetime.datetime.now().date()
# save_src_wh_logs(s_date,e_date)

# save_current_src_wh_logs()

l = get_log()
print l['message']
print len(l['message'])
