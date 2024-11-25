import requests
import numpy as np
import pandas as pd
import time
import tweepy
import os
from datetime import datetime,timedelta

def url_to_df(url,key=None,m=None):
  time_of_trying=0
  response = requests.get(url)
  while time_of_trying<=3600:
    if response.status_code == 200:
        data = response.json()
        if key!=None:
            df=pd.DataFrame(data[key])
        else:
            df=pd.DataFrame(data)
        return df
    else:
        time.sleep(60)
        time_of_trying+=60
        print(f"Error: {response.status_code} this manager is {m}")

def get_num_gw():
    present_fixtures=url_to_df('https://fantasy.premierleague.com/api/fixtures/?future=1')
    num_gw=present_fixtures['event'].min()
    fixtures=url_to_df('https://fantasy.premierleague.com/api/fixtures')
    fixtures=fixtures[fixtures['event']==num_gw-1]
    if fixtures.iloc[-1]['finished']==False:
        num_gw-=1
    return num_gw

def df_to_text(df,num_gw,number_of_managers):
  text=f'Gameweek {num_gw}, captaincy stats :\n'
  text+=f'[Top {number_of_managers}]:\n\n'
  for index,row in df.iterrows():
    text+=row[0]+f' {row[2]:.1f}%\n'
  text+=f'\nTo whom did you give the armband?\n#FPL #GW{num_gw}'
  return text

def prepare(num_gw,pages):
    managers=[]
    n=int(pages/50)+1
    number_of_managers=(n-1)*50
    for i in range(1,n):
        df=url_to_df(f'https://fantasy.premierleague.com/api/leagues-classic/314/standings/?page_new_entries=1&page_standings={i}&phase=1','standings')
        managers=managers+(list([d['entry'] for d in df['results']]))
    d={}
    for manager in managers:
        captain=url_to_df(f'https://fantasy.premierleague.com/api/entry/{manager}/event/{num_gw}/picks/','picks',manager)
        key=captain[captain['is_captain']==True]['element'].iloc[0]
        d[key] = d.get(key, 0) + 1
    captains={}
    for key in d.keys():
        captains[players[players['id']==key]['web_name'].iloc[0]]=d[key]
    df = pd.DataFrame(list(captains.items()), columns=['player', 'captained_by'])
    df=df.sort_values(by='captained_by',ascending=False)
    df['prc']=(df['captained_by']/number_of_managers)*100
    return df

def post(tweet_text):
    bearer_token = os.getenv('BEARER_TOKEN')
    consumer_key =  os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')
    access_token = os.getenv('ACCESS_TOKEN')
    access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')
    TOKEN=os.getenv('TOKEN')
    CHANNEL_ID=os.getenv('CHANNEL_ID')
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'

    params = {'chat_id': CHANNEL_ID,'text': tweet_text}
    telegram = requests.post(url, params=params)
    client = tweepy.Client(bearer_token=bearer_token, consumer_key=consumer_key, consumer_secret=consumer_secret,
                          access_token=access_token, access_token_secret=access_token_secret)
    tweet = client.create_tweet(text=tweet_text)

num_gw=get_num_gw()
players=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
players=players[['id','web_name']]
df=prepare(num_gw,1000)
text=df_to_text(df,num_gw,1000)
post(text)
