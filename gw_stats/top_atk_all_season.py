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

def prepare_atk(num_gameweeks):
  xg={}
  players=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
  players=players[['web_name','team','id','goals_scored','expected_goals']]
  for i in range(1,21):
    xg[df[i]]=round(players[players['team']==i]['expected_goals'].astype(float).sum(),2)
  g={}
  all_fixtures=url_to_df('https://fantasy.premierleague.com/api/fixtures/')
  all_fixtures=all_fixtures[['event','team_a','team_h','team_a_score','team_h_score']]
  fixtures=all_fixtures[all_fixtures['event']<=num_gameweeks]
  fixtures['team_a'] = fixtures['team_a'].map(df).astype(str)
  fixtures['team_h'] = fixtures['team_h'].map(df).astype(str)
  for index,row in fixtures.iterrows():
    g[row['team_a']] = g.get(row['team_a'], 0) + row['team_a_score']
    g[row['team_h']] = g.get(row['team_h'], 0) + row['team_h_score']
  stats=pd.DataFrame({'goals_scored':g,'expected_goals':xg})
  stats.index.name='teams'
  stats['goals_scored']=stats['goals_scored'].astype(int)
  stats=stats.sort_values(by=['goals_scored','expected_goals'],ascending=False)

  top=stats.iloc[:10,:]
  bottom=stats.iloc[-10:,:]
  bottom=bottom.sort_values(by=['goals_scored','expected_goals'],ascending=True)
  return top,bottom

def df_to_text_atk(df,word,num_gameweeks):
  text=f'#FPL #GW{num_gameweeks+1} , {word} 10 - TEAMS - GOALS (xG) [All Season]\n'
  for i,row in df.iterrows():
    g=row['goals_scored'].astype(int)
    xg=row['expected_goals']
    text+=f'\n{i}: {g} ({xg})'
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
top_atk,bottom_atk=prepare_atk(num_gw)
top_text_atk=df_to_text_atk(top_atk,'TOP',num_gw)
post(top_text_atk)
