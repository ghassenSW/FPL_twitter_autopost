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

def prepare_def(num_gw):
  xgc={}
  gc={}
  players=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
  goalkeepers=players[players['element_type']==1]
  for i in range(1,21):
    team_gks=goalkeepers[goalkeepers['team']==i]
    xgc_team=0
    gc_team=0
    for ind,player in team_gks.iterrows():
      id=player['id']
      history=url_to_df(f'https://fantasy.premierleague.com/api/element-summary/{id}/','history')
      history=history[history.index==num_gw-1]
      if len(history)>0:
        xgc_team+=float(history['expected_goals_conceded'].iloc[0])
        gc_team+=float(history['goals_conceded'].iloc[0])
    gc[df[i]]=round(gc_team,2)
    xgc[df[i]]=round(xgc_team,2)
  stats=pd.DataFrame({'goals_conceded':gc,'expected_goals_conceded':xgc})
  stats.index.name='teams'
  stats['goals_conceded']=stats['goals_conceded'].astype(int)
  stats=stats.sort_values(by=['goals_conceded','expected_goals_conceded'],ascending=True)

  top=stats.iloc[:10,:]
  bottom=stats.iloc[-10:,:]
  bottom=bottom.sort_values(by=['goals_conceded','expected_goals_conceded'],ascending=False)
  return top,bottom

def df_to_text_def(df,word,num_gameweeks):
  text=f'#FPL #GW{num_gameweeks} , {word} 10 - TEAMS - GOALS CONCEDED (xGC)\n'
  for i,row in df.iterrows():
    gc=row['goals_conceded'].astype(int)
    xgc=row['expected_goals_conceded']
    text+=f'\n{i}: {gc} ({xgc})'
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

teams=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','teams')
teams['emoji']=['🔫 #ARS ','🦁 #AVL ','🍒 #BOU ','🐝 #BRE ','🕊 #BHA ','🔵 #CHE ','🦅 #CRY ','🍬 #EVE ','⚪️ #FUL ','🚜 #IPS ',
                '🦊 #LEI ','🔴 #LIV ','🌑 #MCI ','👹 #MUN ','⚫️ #NEW ','🌳 #NFO ','😇 #SOU ','🐓 #TOT ','⚒️ #WHU ','🐺 #WOL ']
df=dict(zip(teams['id'],teams['emoji']))

num_gw=get_num_gw()-1
top_def,bottom_def=prepare_def(num_gw)
bottom_text_def=df_to_text_def(bottom_def,'BOTTOM',num_gw)
post(bottom_text_def)


