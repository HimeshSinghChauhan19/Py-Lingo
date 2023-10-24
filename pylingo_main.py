'''
IMPORTANT: This program needs isStreakDone.txt to work correctly, they need to be in the same folder...
'''

from datetime import datetime
import json
import os
from json import JSONDecodeError
import requests
import pyautogui as pg
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

'''
Latest: 
    Duolingo Team changed the way of logging in a user, probably cause they got to know bout this vulnerability. 
    This is dead for now, and I haven't got enough time to work on this. 
Future: 
    Inorder to make this, will have to figure out the new way that they are using to login and to get some idea that would bypass that way to 
    automate the process using python.

Currently I have worked till the API calls, and next thing shall be having the credentials prompted from the User 
to get them the details of their Account, 

Update: 

Got to somehow access the login api and successfully passed the payload to have the user logged in.
With that in hand it becomes easy to access the stored data in the database of Duolingo and maybe the data of other
users can be fetched, however that may not be a case of Authentication, but maybe of Authorization.
Assuming that they might have put some inner restrictions on who can access data, ASSUMIN:57:18G.

There can be a choice of things that this can provide like performing some actions related to the account of 
a user that is logges in already with their credentials.

!! Update Needed !! 
Currently I haven't been able to find a way to automatically somehow bypass the security of authorization
Bcz duolingo generates some unique_id in the starting of the login process is which is being shared later in the time of 
login to make the things a bit difficult for the someone trying to automate the process.

    A possible solution:
        Maybe the previous windows like the duolingo.com/learn page can be accessed by some other language like JS
        to get the required tokens and unique_ids but the problem is that currently for a WebFormatter I just know 
        BeautifulSoup and with JS I don't have any idea related to this context.
    May Later work on this issue

But for now:
    The user can login into their account in a normal web browser and get the jwt token by entering the provided 
    JavaScript one liner code that will get the jwt token for their current session. 
    
    and bcz the session doesn't get expired as long as the user is logged in then this becomes a possible choice for now.
'''


# Txt file work, for non-volatile data storage
curr_date=os.popen('date /T').read().split()[-1]
curr_time=os.popen('time /T').read().split()[-1]
prev_date,isDone=open('isStreakDone.txt','r').read().split(',')

# If the streak extension mail is sent for today then don't bother to do this work now
if(curr_date==prev_date and isDone=='done'):
    exit()
# file.write(f'{curr_date},done')
# file.close()

class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)


class OtherUserException(DuolingoException):
    """
    This exception is raised when set_username() has been called to get info on another user, but a method has then
    been used which cannot give data on that new user.
    
    -Currently Cause I haven't been able to find a way to get the credentials of other users, so this is a Prob.
    """
    pass


class Duolingo(object):
    USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 " \
                 "Safari/537.36"

    def __init__(self, username, password=None, *, jwt=None, session_file=None):
        """
        :param username: Username to use for duolingo
        :param password: Password to authenticate as user.
        :param jwt: Duolingo login token. Will be checked and used if it is valid.
        :param session_file: File path to a file that the session token can be stored in, to save repeated login
        requests.
        """
        self.username = username
        self._original_username = username
        self.password = password
        self.session_file = session_file
        self.session = requests.Session()
        self.leader_data = None
        self.jwt = jwt

        # if any of this is available then can try for a login, but actually jwt is necessary otherwise it's uncertain
        if password or jwt or session_file:
            self._login()
        else:
            print("Incorrect pass or JWT!")
            exit()
#         print("returning from constr.")
        self.user_data = Struct(**self._get_data())
        self.voice_url_dict = None
    
    # to make a custom request to another url with the same session
    def make_custReq(self,url):
        headers={}
        headers['User-Agent'] = self.USER_AGENT
        headers['User-Agent'] = self.USER_AGENT
        return requests.get(url,headers=headers,cookies=self.session.cookies)
    
    def _make_req(self, url, data=None):
        headers = {}
        # if we have a jwt token then gonna use that for the authorization header of http request
        if self.jwt is not None:
            headers['Authorization'] = 'Bearer ' + self.jwt
            
        # setting the user agent for the post req
        headers['User-Agent'] = self.USER_AGENT
        req = requests.Request('POST' if data else 'GET',
                               url,
                               json=data,
                               headers=headers,
                               cookies=self.session.cookies)
        prepped = req.prepare()
        resp = self.session.send(prepped)
        
        # If there may be a captcha problem, then to handle that
        if resp.status_code == 403 and resp.json().get("blockScript") is not None:
            print("Problem with response data. Login Failed, try again.")
        return resp

    def _login(self):
        """
        Authenticate through ``https://www.duolingo.com/login``.
        """
#         print("Loggin in... ;)")
        if self.jwt is None:
            self._load_session_from_file()
            
        if self._check_login():
            return True
        self.jwt = None

        login_url = "https://www.duolingo.com/2017-06-30/login-experiment?fields="
        data = {"identifier": self.username, "password": self.password}
        request = self._make_req(login_url, data)
        # print(request)
        # exit()
        attempt = request.json()

        '''
        This will be the response when there will be some problem in the request.
        {
            "failure": "missing_field",
            "message": "Failed login"
        }
        '''
        if "failure" not in attempt:
            self.jwt = request.headers['jwt']
            self._save_session_to_file()
            return True


        
    # simply based on idea of storing some information in a separate file and loading it from there
    def _load_session_from_file(self):
        if self.session_file is None:
            return
        try:
            with open(self.session_file, "r") as f:
                self.jwt = json.load(f).get("jwt_session")
        except (OSError, JSONDecodeError):
            return

    def _save_session_to_file(self):
        if self.session_file is not None:
            with open(self.session_file, "w") as f:
                json.dump({"jwt_session": self.jwt}, f)
        else:
            pass
    # if I can make a req successfully means everything is fine else not
    def _check_login(self):
        resp = self._make_req(self.get_user_url())
        return resp.status_code == 200

    def get_user_url(self):
        return "https://duolingo.com/users/%s" % self.username

    def set_username(self, username):
        self.username = username
        self.user_data = Struct(**self._get_data())

    
    def _get_data(self):
        """
        Get user's data from ``https://www.duolingo.com/users/<username>``.
        """
        get = self._make_req(self.get_user_url())
        if get.status_code == 404:
            raise Exception('User not found')
        else:
            return get.json()

    @staticmethod
    def _make_dict(keys, array):
        data = {}

        for key in keys:
            if type(array) == dict:
                data[key] = array[key]
            else:
                data[key] = getattr(array, key, None)

        return data


    def get_settings(self):
        """Get user settings."""
        keys = ['notify_comment', 'deactivated', 'is_follower_by',
                'is_following']

        return self._make_dict(keys, self.user_data)


    def get_user_info(self):
        """Get user's informations."""
        fields = ['username', 'bio', 'id', 'num_following', 'cohort',
                  'language_data', 'num_followers', 'learning_language_string',
                  'created', 'contribution_points', 'gplus_id', 'twitter_id',
                  'admin', 'invites_left', 'location', 'fullname', 'avatar',
                  'ui_language']

        return self._make_dict(fields, self.user_data)

    def get_streak_info(self):
        """Get user's streak informations."""
        fields = ['daily_goal', 'site_streak', 'streak_extended_today']
        return self._make_dict(fields, self.user_data)

    def _is_current_language(self, abbr):
        """Get if user is learning a language."""
        return abbr in self.user_data.language_data.keys()

    def get_calendar(self, language_abbr=None):
        """Get user's last actions."""
        if language_abbr:
            if not self._is_current_language(language_abbr):
                self._switch_language(language_abbr)
            return self.user_data.language_data[language_abbr]['calendar']
        else:
            return self.user_data.calendar



attrs = [
    'settings', 'user_info', 'streak_info',
    'calendar', 
]

for attr in attrs:
    getter = getattr(Duolingo, "get_" + attr)
    prop = property(getter)
    setattr(Duolingo, attr, prop)


ur_name,ur_pass,ur_browser_jwt=input("Enter Username,password and browser JWT(space separated) ").split()

obj1=Duolingo(ur_name,password=ur_pass,jwt=ur_browser_jwt)

while(True):
     
    ''' you's Section '''
    # just keep checking for whether streak is done for today or not, and whenever it will be done, send me a mail
    data=json.loads(obj1.make_custReq(f'https://www.duolingo.com/users/{ur_name}').text)
    your_streak = data['streak_extended_today']
    your_calendar = data['language_data']['es']['calendar']
    your_last_streak = your_calendar[-1]['datetime']
    day_of_extension,your_timing = str(datetime.fromtimestamp(your_last_streak//1000)).split('-')[2].split()[0],str(datetime.fromtimestamp(your_last_streak//1000)).split('-')[2].split()[1]
    day_of_extension = day_of_extension[1:] if(day_of_extension[0]=='0') else day_of_extension
    
    if(your_streak==True):
        ''' Send a mail '''     
        smtp_user = '<your_mail>'
        smtp_password = '<pass>'

        msg = MIMEMultipart("alternative")
        msg["Subject"] = 'Regarding your Streak Extension 🙂'
        msg["From"] = smtp_user
        msg["To"] = "<your_mail>"
        message=f'you have extended streak for today😎\nAt {curr_time}.'
        msg.attach(MIMEText(message, 'plain'))
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.ehlo()
        s.starttls()
        s.login(smtp_user, smtp_password)
        s.sendmail(smtp_user, "<your_mail>", msg.as_string())
        s.quit()

        ''' Send a whatsApp Message '''
        requests.get(f'https://api.callmebot.com/whatsapp.php?phone=<your_number>&text={message}&apikey=<ur_api>')


        # FINAL FILE UPDATION STUFF
        # Then put a message in the isStreakDone.txt file so that we won't worry about now for today's Streak
        file=open('isStreakDone.txt','w')
        file.write(f"{curr_date},done")
        file.close()
        exit()
        
    
    ''' getting the last 15 days streak timings '''
#     for date in your_calendar:
#         date_of_streak,timing=str(datetime.fromtimestamp(date['datetime']//1000)).split('-')[2].split()
#         pg.press('win')
#         pg.typewrite(f'On {date_of_streak} extended streak at {timing}',interval=0.04)
    
    
    ''' Currently won't be doing the time summaries stuff with gui, maybe later '''
    # print("Last 15 days summary of time when the streak was extended for that day...")
    # to make the popups for the last 15 days streak extending time summary
    # for ind,day in enumerate(calendar_data,start=1):
    #     pg.press('win')
    #     time.sleep(1)
    #     output_str=f'Streak extended on day {ind}: {datetime.fromtimestamp(day["datetime"]//1000)}'
    #     pg.typewrite(output_str,interval=0.04)
    #     time.sleep(5)

    #     print(datetime.fromtimestamp(day['datetime']//1000))
    #     print(day['datetime'])
    
    # will repeat after every 1 Hour
    # time.sleep(3600)