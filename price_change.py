# you need to fix when the gw changes it gives the price change of the whole gw

import requests
import numpy as np
import pandas as pd
import time
import tweepy
from datetime import datetime,timedelta
import json

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

def prepare(players):
  players=players[['team','web_name','cost_change_event','now_cost']]
  players.loc[:,'now_cost']=players.loc[:,'now_cost']/10
  players=players[players['cost_change_event']!=0]
  players = players.rename(columns={'team': 'team_id'})
  players.loc[:,'team']=players['team_id'].map(short_name.iloc[0])
  players=players.sort_values(by=['cost_change_event','now_cost'],ascending=False)
  return players

def df_to_text(df):
  text=''
  risers=df[df['cost_change_event']==1]
  fallers=df[df['cost_change_event']==-1]
  current_time=datetime.now().date()
  if(len(risers)!=0):
    text+=(f'\n📈 Price Risers! ({current_time}) :\n')
    for index,row in risers.iterrows():
      text+=(f'⬆️ {row["web_name"]} #{row["team"]} £{row["now_cost"]}m\n')
  if(len(fallers)!=0):
    text+=(f'\n📉 Price Fallers! ({current_time}) :\n')
    for index,row in fallers.iterrows():
      text+=(f'⬇️ {row["web_name"]} #{row["team"]} £{row["now_cost"]}m\n')
  text+=f'\n#FPL #GW{num_gameweek} #FPL_PriceChanges'
  return text

def df_to_text_all(df):
  current_time=datetime.now().date()
  text=f'💰 FPL Daily Price Changes ({current_time})\n'
  risers=df[df['cost_change_event']==1]
  fallers=df[df['cost_change_event']==-1]
  if(len(risers)!=0):
    text+=(f'\n📈 Risers:\n')
    for index,row in risers.iterrows():
      text+=(f'⬆️ {row["web_name"]} #{row["team"]} £{row["now_cost"]}m\n')
  if(len(fallers)!=0):
    text+=(f'\n📉 Fallers:\n')
    for index,row in fallers.iterrows():
      text+=(f'⬇️ {row["web_name"]} #{row["team"]} £{row["now_cost"]}m\n')
  text+=f'\n#FPL #GW{num_gameweek} #FPL_PriceChanges'
  return text

def split_text_into_tweets(text, limit=280):
    lines = text.split('\n')
    tweets = []
    current_tweet = ""

    for line in lines:
      if len(current_tweet) + len(line) + 1 <= limit:
        current_tweet += f"{line}\n"
      else:
        tweets.append(current_tweet.strip())
        current_tweet = f"{line}\n"
    if current_tweet:
      tweets.append(current_tweet.strip('\n'))
    last_two_tweets=tweets[-2]+'\n'+tweets[-1]
    tweets.pop()
    tweets.pop()
    lines=last_two_tweets.split('\n')
    num_lines=len(lines)//2+1
    new_tweet=''
    for line in lines[:num_lines]:
      new_tweet+=f'{line}\n'
    new_tweet=new_tweet.strip('\n')
    tweets.append(new_tweet)
    new_tweet=''
    for line in lines[num_lines:]:
      new_tweet+=f'{line}\n'
    new_tweet=new_tweet.strip('\n')
    tweets.append(new_tweet)

    return tweets

def post(df):
    TOKEN='7187953343:AAFSZ7I0FzzsQes_SrhG2dX74IRIcLgAa54'
    CHANNEL_ID='-1001534852752'
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    bearer_token = "AAAAAAAAAAAAAAAAAAAAAHpZwQEAAAAAa%2BL2Fn26r7fRpOz6okyMP4gT8cI%3DgH6vulMQnvuTNGNywG06fnGEiuuYD28RHt8nf4wDzeP8DLJRJy"
    consumer_key = "5H7fUfbrQ2XF5WqSG67ttM2R1"
    consumer_secret = "Bw1MR5iPieCLgzodClVRjWIaPVrIPk7r7bif9t261WbgqiGob0"
    access_token = "1844404415349817349-41SFbOP4Fmw7ptB4Jhgi52NQtn2l1V"
    access_token_secret = "mrWXSuAUgvq9riop7xnO1mJ7XNPCdc4ZwZmjv4zmttdEJ"

    client = tweepy.Client(bearer_token=bearer_token, consumer_key=consumer_key, consumer_secret=consumer_secret,
                        access_token=access_token, access_token_secret=access_token_secret)

    tweet_text_all=df_to_text_all(df)
    
    params = {
        'chat_id': CHANNEL_ID,
        'text': tweet_text_all
    }
    telegram = requests.post(url, params=params)


    if(len(tweet_text_all)<=280):
       response=client.create_tweet(text=tweet_text_all)
       print(f'posted single tweet: {tweet_text_all}')

    else:
      risers=df[df['cost_change_event']==1]
      fallers=df[df['cost_change_event']==-1]
      risers_text=df_to_text(risers)
      fallers_text=df_to_text(fallers)

      if ((len(risers)>0) and (len(risers_text) <=280)):
          response = client.create_tweet(text=risers_text)
          print(f"Posted single tweet: {risers_text}")
      else:
          tweets = split_text_into_tweets(risers_text)
          last_tweet = client.create_tweet(text=tweets[0])
          print(f"Posted tweet:",tweets[0])
          for tweet in tweets[1:]:
              last_tweet = client.create_tweet(text=tweet, in_reply_to_tweet_id=last_tweet.data['id'])
              print(f"Posted tweet in thread: ",tweet)

      if ((len(fallers)>0) and (len(fallers_text) <=280)):
          response = client.create_tweet(text=fallers_text)
          print(f"Posted single tweet: {fallers_text}")
      else:
          tweets = split_text_into_tweets(fallers_text)
          last_tweet = client.create_tweet(text=tweets[0])
          print(f"Posted tweet:",tweets[0])
          for tweet in tweets[1:]:
              last_tweet = client.create_tweet(text=tweet, in_reply_to_tweet_id=last_tweet.data['id'])
              print(f"Posted tweet in thread: ",tweet)


teams=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','teams')
short_name=dict(zip(teams['id'],teams['short_name']))
short_name=pd.DataFrame(short_name,index=[0])
present_fixtures=url_to_df('https://fantasy.premierleague.com/api/fixtures/?future=1')
num_gameweek=present_fixtures['event'].min()

with open('data.json', 'r') as file:
    data = json.load(file)
old_stats=pd.DataFrame(data['elements'])
old=prepare(old_stats)

while True:
    time.sleep(60)

    new_stats=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
    new=prepare(new_stats)
    current_time=datetime.now()
    print(current_time)

    difference = pd.concat([new, old]).drop_duplicates(keep=False)

    if len(difference)>0:
      post(difference)
      print('posted a price change at this day')
      break
    elif current_time.hour>=2:
      print('theres no price changes at this day')
      break
