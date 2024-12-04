import requests
import numpy as np
import pandas as pd
import tweepy
import time
from datetime import datetime,timedelta
import json
import subprocess
import os
from collections import defaultdict

def url_to_df(url,key=None):
  time_of_trying=0
  while time_of_trying<=3600:
    response = requests.get(url)
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
        print(f"Error: {response.status_code}")

def get_num_gw():
    present_fixtures=url_to_df('https://fantasy.premierleague.com/api/fixtures/?future=1')
    num_gw=present_fixtures['event'].min()
    fixtures=url_to_df('https://fantasy.premierleague.com/api/fixtures')
    fixtures=fixtures[fixtures['event']==num_gw-1]
    if fixtures.iloc[-1]['finished']==False:
        num_gw-=1
    return num_gw

def prepare(df):
  df['full_name']=df['first_name']+' '+df['second_name']
  df['team']=df['team'].map(my_map.iloc[0])
  df=df[['chance_of_playing_next_round','team','full_name','news']]
  df.loc[:,'chance_of_playing_next_round']=df.loc[:,'chance_of_playing_next_round'].fillna(101)
  df.loc[:,'news']=df.loc[:,'news'].fillna('')
  return df

def split_text_into_tweets(text, limit=280):
    lines = text.split('|')
    tweets = []
    current_tweet = ""

    for line in lines:
        if len(current_tweet) + len(line) + 1 <= limit:
            current_tweet += f"{line}"
        else:
            tweets.append(current_tweet.strip())
            current_tweet = f"{line}"
    if current_tweet:
        tweets.append(current_tweet.strip('\n'))
    if len(tweets[-1])>limit:
        pos=tweets[-1].rfind('👟')
        f_tweet=tweets[:pos]
        s_tweet=tweets[pos:]
        tweets[-1]=f_tweet
        tweets.append(s_tweet)
    return tweets

def df_to_text(players,gw):
    tweet_text='🚨 Injury Updates\n\n'
    match_tag=f'#GW{gw} #FPL #FPL_InjuryUpdates'
    for index,row in players.iterrows():
        player_name=row['full_name']
        team_name=teams_short_names[row['team']]
        tweet_text+=f'👟 {player_name} (#{team_name})\n'
        if(row['chance_of_playing_next_round']==100):
            tweet_text+=f'✅ Availability is now 100%\n'
        elif row['chance_of_playing_next_round']==0:
           stat=row['news']
           tweet_text+=f'⛔️ {stat}\n'
        else:
            stat=row['news']
            tweet_text+=f'🤕 {stat}\n'
        tweet_text+='\n|'
    tweet_text=tweet_text.strip('\n|')
    tweet_text+='\n\n'+match_tag
    return tweet_text

def post(tweet_text):
    bearer_token = os.getenv('BEARER_TOKEN')
    consumer_key =  os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')
    access_token = os.getenv('ACCESS_TOKEN')
    access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')
    TOKEN=os.getenv('TOKEN')
    CHANNEL_ID=os.getenv('CHANNEL_ID')
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'

    telegram_text=tweet_text.replace('|','')
    params = {'chat_id': CHANNEL_ID,'text': telegram_text}
    telegram = requests.post(url, params=params)
    client = tweepy.Client(bearer_token=bearer_token, consumer_key=consumer_key, consumer_secret=consumer_secret,
                        access_token=access_token, access_token_secret=access_token_secret)

    tweets=split_text_into_tweets(tweet_text)
    try: 
        last_tweet = client.create_tweet(text=tweets[0])
    except Exception as e:
        print(e)
    print(f"Posted tweet:--------------------------------------------------------------------------------------\n{tweets[0]}")
    for tweet in tweets[1:]:
        time.sleep(10)
        try:
            last_tweet = client.create_tweet(text=tweet, in_reply_to_tweet_id=last_tweet.data['id'])
        except Exception as e:
            print(e)
        print(f"Posted tweet in thread:------------------------------------------------------------------------\n{tweet}")

def get_new_games():
  num_gw=get_num_gw()
  present_fixtures=url_to_df('https://fantasy.premierleague.com/api/fixtures')
  present_fixtures=present_fixtures[present_fixtures['event']==num_gw]
  present_fixtures['kickoff_time']=pd.to_datetime(present_fixtures['kickoff_time'])
  present_fixtures['kickoff_time']=present_fixtures['kickoff_time']-pd.to_timedelta(1, unit='h')
  current_time=pd.Timestamp.now(tz='UTC')
  past_time=current_time-pd.to_timedelta(40, unit='m')
  new_games=present_fixtures[present_fixtures['kickoff_time']<current_time].index.values.tolist()
  old_games=present_fixtures[present_fixtures['kickoff_time']<past_time].index.values.tolist()
  games=[game%10 for game in new_games if game not in old_games]
  return games

def prepare_current_gw(num_gw):
    gw_matches=url_to_df('https://fantasy.premierleague.com/api/fixtures/')
    gw_matches=gw_matches[gw_matches['event']==num_gw]
    gw_matches['day']=gw_matches['kickoff_time'].apply(lambda x:datetime.strptime(x,'%Y-%m-%dT%H:%M:%SZ').day)
    gw_matches['day']=gw_matches['day']-gw_matches['day'].min()+1
    gw_matches=gw_matches[['id','kickoff_time','minutes','started','finished_provisional','team_a','team_h','team_a_score','team_h_score','stats','day']]
    gw_matches['num_of_match']=gw_matches.index%10
    gw_matches['num_of_set']=gw_matches['kickoff_time'].factorize()[0]+1
    gw_matches['team_a_score']=gw_matches['team_a_score'].fillna(0)
    gw_matches['team_h_score']=gw_matches['team_h_score'].fillna(0)
    gw_matches['team_a_score']=gw_matches['team_a_score'].astype(int)
    gw_matches['team_h_score']=gw_matches['team_h_score'].astype(int)
    gw_matches['kickoff_time'] = pd.to_datetime(gw_matches['kickoff_time']).dt.tz_localize(None)
    current_time = datetime.now().replace(microsecond=0) 
    # current_time=current_time-timedelta(hours=1)
    gw_matches['waiting_time']=gw_matches['kickoff_time']-current_time
    gw_matches['waiting_time']=(gw_matches['waiting_time'].apply(lambda x:x.total_seconds())).astype(int)
    return gw_matches

def post_on_time(post_time,file):
  current_time = datetime.now().replace(microsecond=0)
  if (current_time>post_time) and (current_time-timedelta(minutes=30)<post_time):
    subprocess.run(["python",f"gw_stats/{file}.py"])


num_gw=get_num_gw()
matches=url_to_df(f'https://www.sofascore.com/api/v1/unique-tournament/17/season/61627/events/round/{num_gw}','events')
all_games_of_current_gw=prepare_current_gw(num_gw-1)
last_game_time=all_games_of_current_gw.iloc[-1]['kickoff_time']
# last gw
time_top_atk_last_gw=(last_game_time + timedelta(days=1)).replace(hour=6, minute=0, second=0)
time_bottom_atk_last_gw=time_top_atk_last_gw+timedelta(hours=2)
time_top_def_last_gw=time_bottom_atk_last_gw+timedelta(hours=2)
time_bottom_def_last_gw=time_top_def_last_gw+timedelta(hours=2)
post_on_time(time_top_atk_last_gw,'top_atk_last_gw')
post_on_time(time_bottom_atk_last_gw,'bottom_atk_last_gw')
post_on_time(time_top_def_last_gw,'top_def_last_gw')
post_on_time(time_bottom_def_last_gw,'bottom_def_last_gw')
# players stats
time_points_stats=time_bottom_def_last_gw+timedelta(hours=2)
time_goals_stats=time_points_stats+timedelta(hours=2)
time_assists_stats=time_goals_stats+timedelta(hours=2)
post_on_time(time_points_stats,'points_stats')
post_on_time(time_goals_stats,'goals_stats')
post_on_time(time_assists_stats,'assists_stats')
# all season
time_top_atk_all_season=time_top_atk_last_gw+timedelta(hours=24)
time_bottom_atk_all_season=time_top_atk_all_season+timedelta(hours=2)
time_top_def_all_season=time_bottom_atk_all_season+timedelta(hours=2)
time_bottom_def_all_season=time_top_def_all_season+timedelta(hours=2)
post_on_time(time_top_atk_all_season,'top_atk_all_season')
post_on_time(time_bottom_atk_all_season,'bottom_atk_all_season')
post_on_time(time_top_def_all_season,'top_def_all_season')
post_on_time(time_bottom_def_all_season,'bottom_def_all_season')

# lineups & goal alerts
new_games=get_new_games()
if len(new_games)>0:
    print('lineups are processing')
    subprocess.run(["python","confirmed_lineups.py"])
    if new_games[0]==0:
        print('lineups are posted and most captained will begin processing')
        subprocess.run(["python","most_captained.py"])
        print('most captained are posted and goal alerts will begin processing')
    else:
        print('lineups are posted and goal alerts will begin processing')
    subprocess.run(["python", "goal_alerts.py"])

# injury updates:
teams=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','teams')
teams_short_names=dict(zip(teams['name'],teams['short_name']))
my_map=dict(zip(teams['id'],teams['name']))
my_map=pd.DataFrame(my_map,index=[0])
num_gameweek=get_num_gw()

with open('data.json', 'r') as file:
    saved_data = json.load(file)
old_stats=pd.DataFrame(saved_data['elements'])
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
