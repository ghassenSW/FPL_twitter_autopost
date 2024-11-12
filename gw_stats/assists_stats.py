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

def prepare_assists(num_gw):
  players=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
  ids=players['id']
  a_xa={}
  for id in ids:
    player=url_to_df(f'https://fantasy.premierleague.com/api/element-summary/{id}/','history')
    player_name=players_id[id]
    assists=player.iloc[-1,:]['assists']
    xa=player.iloc[-1,:]['expected_assists']
    a_xa[player_name]=[xa,assists]
  a_xa=pd.DataFrame(a_xa).T
  a_xa.columns=['expected_assists','assists']
  a_xa=a_xa.sort_values(by=['expected_assists','assists'],ascending=False)
  a_xa=a_xa.iloc[:10,:]
  return a_xa

def assists_to_text(df,num_gw):
  text=f'#FPL #GW{num_gw} , TOP 10 - PLAYERS - XA (ASSISTS)\n'
  for i,row in df.iterrows():
    a=row['assists'].astype(int)
    xa=row['expected_assists']
    text+=f'\n{i}: {xa} ({a})'
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
assists=prepare_assists(num_gw)
assists_text=assists_to_text(assists,num_gw)
post(assists_text)
