import os, sys, json, tweepy, requests, datetime, radar, random
from tweepy import StreamListener
from tweepy import Stream

CONSUMER_KEY = None
CONSUMER_SECRET = None
ACCESS_KEY = None
ACCESS_SECRET = None
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
    TWITTER_TARGETS = data['TWITTER_TARGETS']
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

    def get_random_visitor(self, start_date, end_date):
        d = start_date
        random_date = radar.random_date(start=start_date, stop=end_date)
        wh_uri = WH_LOGS_SOURCE+random_date.strftime('%Y-%m-%d')+'.json'
        vistors = None
        txt = None
        try:
            response = requests.get(wh_uri)
            response.raise_for_status()
            rv_json = random.choice(response.json())
            if rv_json['place'] != 'White House':
                get_random_visitor(start_date, end_date)
            else:
                # get the date
                rvdate = datetime.datetime.strptime(rv_json['date'],'%Y-%m-%d')
                v_date = rvdate.strftime('%b %d, %Y')
                v = rv_json['visitor']
                vname = v['first_name']+' '+v['last_name']
                title = v['title'] if v['title'] else ''
                org = v['organization']['name'] if v['organization'] else ''
                txt = '{0} {1} {2} {3} visited the White House'.format(v_date, vname, title, org)
                            
        except requests.exceptions.HTTPError as err:
            get_random_visitor(start_date, end_date)
        
        return txt

    def on_status(self, status):
        status_id = status.id_str
        user_id = status.user.id_str
        scr_name = status.user.screen_name
        txt = self.get_random_visitor(s_date, e_date)
        while txt == None:
            txt = self.get_random_visitor(s_date, e_date)
        txt = '@{0} '.format(scr_name)+txt
        txt = ' '.join(txt.split())
        api.update_status(status=txt, in_reply_to_status_id = status_id)

    def on_error(self, status_code):
        if status_code == 420:
            # print "Error: 420"
            return False            

if __name__ == '__main__':
    # listener = StdOutListener()
    listener = StreamListener()
    twitterStream = Stream(auth, listener)
    twitterStream.filter(track=['#whlogs'])