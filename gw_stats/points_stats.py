import requests
import numpy as np
import pandas as pd
import time
import tweepy
import os
from datetime import datetime,timedelta

def url_to_df(url,key=None):
  response = requests.get(url)
  if response.status_code == 200:
      data = response.json()
      if key!=None:
        df=pd.DataFrame(data[key])
      else:
        df=pd.DataFrame(data)
      return df
  else:
      print(f"Error: {response.status_code}")

def get_num_gw():
    present_fixtures=url_to_df('https://fantasy.premierleague.com/api/fixtures/?future=1')
    num_gw=present_fixtures['event'].min()
    fixtures=url_to_df('https://fantasy.premierleague.com/api/fixtures')
    fixtures=fixtures[fixtures['event']==num_gw-1]
    if fixtures.iloc[-1]['finished']==False:
        num_gw-=1
    return num_gw

def prepare_pts(num_gw):
  players=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
  ids=players['id']
  pts={}
  for id in ids:
    player=url_to_df(f'https://fantasy.premierleague.com/api/element-summary/{id}/','history')
    player_name=players_id[id]
    points=player.iloc[-1,:]['total_points']
    pts[player_name]=[points]
  pts=pd.DataFrame(pts).T
  pts.columns=['points']
  pts=pts.sort_values(by='points',ascending=False)
  pts=pts.iloc[:10,:]
  return pts

def pts_to_text(df,num_gw):
  text=f'#FPL #GW{num_gw} , TOP 10 - PLAYERS - POINTS\n'
  for i,row in df.iterrows():
    pts=row['points'].astype(int)
    text+=f'\n{i}: {pts}'
  return text

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

players=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
players_id=dict(zip(players['id'],players['web_name']))

num_gw=get_num_gw()-1
points=prepare_pts(num_gw)
points_text=pts_to_text(points,num_gw)
post(points_text)
