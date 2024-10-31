import requests
import numpy as np
import pandas as pd
import tweepy
import time
from datetime import datetime
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

def prepare(df):
  df['full_name']=df['first_name']+' '+df['second_name']
  df['team']=df['team'].map(map.iloc[0])
  df=df[['chance_of_playing_next_round','team','full_name','news']]
  df.loc[:,'chance_of_playing_next_round']=df.loc[:,'chance_of_playing_next_round'].fillna(101)
  df.loc[:,'news']=df.loc[:,'news'].fillna('')
  return df

def split_lines(text):
  lines=text.split('\n')
  tweets=[]
  for line in lines[:-1]:
    tweets.append(line.strip())
  return tweets

def split_text_into_tweets(text):
    lines = text.split('|')
    tweets = []
    for line in lines:
      tweets.append(line.strip())
    return tweets

def df_to_text(players,gw):
    tweet_text=''
    match_tag=f'#GW{gw} #FPL #FPL_InjuryUpdates'
    for index,row in players.iterrows():
        tweet_text+='🚨 Injury Updates\n'
        player_name=row['full_name']
        team_name=row['team']
        tweet_text+=f'👟 Player : {player_name} ({team_name})\n'
        if(row['chance_of_playing_next_round']==100):
            tweet_text+=f'✅ Update: Availability is now 100%\n'
        elif row['chance_of_playing_next_round']==0:
           stat=row['news']
           tweet_text+=f'⛔️ Update: {stat}\n'
        else:
            stat=row['news']
            tweet_text+=f'🤕 Update: {stat}\n'
        tweet_text+=match_tag
        tweet_text+='\n|'
    tweet_text=tweet_text.strip('\n|')
    return tweet_text

def tweet_to_telegram(tweet_text):
  tweets=split_text_into_tweets(tweet_text)
  output=''
  for tweet in tweets[:-1]:
    lines=split_lines(tweet)
    for line in lines:
      output+=line+'\n'
    output+='\n'
  last_lines=tweets[-1].split('\n')
  for line in last_lines[:-1]:
    output+=line+'\n'
  output+='\n'+last_lines[-1]
  return output

def post(tweet_text):
    bearer_token = "AAAAAAAAAAAAAAAAAAAAAHpZwQEAAAAAa%2BL2Fn26r7fRpOz6okyMP4gT8cI%3DgH6vulMQnvuTNGNywG06fnGEiuuYD28RHt8nf4wDzeP8DLJRJy"
    consumer_key = "5H7fUfbrQ2XF5WqSG67ttM2R1"
    consumer_secret = "Bw1MR5iPieCLgzodClVRjWIaPVrIPk7r7bif9t261WbgqiGob0"
    access_token = "1844404415349817349-41SFbOP4Fmw7ptB4Jhgi52NQtn2l1V"
    access_token_secret = "mrWXSuAUgvq9riop7xnO1mJ7XNPCdc4ZwZmjv4zmttdEJ"

    TOKEN='7187953343:AAFSZ7I0FzzsQes_SrhG2dX74IRIcLgAa54'
    CHANNEL_ID='-1001534852752'
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'

    telegram_text=tweet_to_telegram(tweet_text)
    params = {'chat_id': CHANNEL_ID,'text': telegram_text}
    telegram = requests.post(url, params=params)
    client = tweepy.Client(bearer_token=bearer_token, consumer_key=consumer_key, consumer_secret=consumer_secret,
                        access_token=access_token, access_token_secret=access_token_secret)

    tweets = split_text_into_tweets(tweet_text)
    last_tweet = client.create_tweet(text=tweets[0])
    print(f"Posted tweet:--------------------------------------------------------------------------------------\n{tweets[0]}")
    for tweet in tweets[1:]:
        last_tweet = client.create_tweet(text=tweet, in_reply_to_tweet_id=last_tweet.data['id'])
        print(f"Posted tweet in thread:------------------------------------------------------------------------\n{tweet}")

teams=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','teams')
map=dict(zip(teams['id'],teams['name']))
map=pd.DataFrame(map,index=[0])
present_fixtures=url_to_df('https://fantasy.premierleague.com/api/fixtures/?future=1')
num_gameweek=present_fixtures['event'].min()

with open('data/data.json', 'r') as file:
    data = json.load(file)
old_stats=pd.DataFrame(data['elements'])
new_stats=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
old=prepare(old_stats)
new=prepare(new_stats)

conditions=new[['chance_of_playing_next_round','news']]!=old[['chance_of_playing_next_round','news']]
first_condition=new[conditions['chance_of_playing_next_round']]
second_condition=new[conditions['news']]
players = pd.concat([first_condition, second_condition], axis=0, ignore_index=True)
players = players.drop_duplicates()
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if len(players)>0:
    tweet_text=df_to_text(players,num_gameweek)
    post(tweet_text)
    print(f'posted an update at {current_time}')
else:
    print(f'theres no post at {current_time}')
