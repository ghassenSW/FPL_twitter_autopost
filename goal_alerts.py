# This code works with utc time and to make it work with local tunisian time you need to uncomment line 49 in prepare(gw) of current_time
# Every timme you want to start this code check the num_gw, num_of_match and num_of_set parameters and set them as present values (inital ones are min() and 0)

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

def prepare_stats(id,gw):
  game=gw[gw['id']==id]['stats']
  game=game.iloc[0]
  game=str(game)
  game=eval(game) # only when trying with test data
  if len(game)==0:
    return []
  game=pd.DataFrame(game)
  game=game.transpose()
  game.columns=game.iloc[0]
  game=game[1:]
  return game

def prepare(num_gw):
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

def current_set(num_gw,num_of_set):
    gw_matches=prepare(num_gw)
    gw_matches=gw_matches[gw_matches['num_of_set']==num_of_set]
    return gw_matches

def get_num_of_set(num_gw,num_of_match):
  games=prepare(num_gw)
  num_of_set=games.iloc[num_of_match]['num_of_set']
  return num_of_set

def live_gws(gw,upcoming_games):
    gw_matches=prepare(gw)
    gw_matches=gw_matches[gw_matches['num_of_match'].isin(upcoming_games)]
    gw_matches=gw_matches[gw_matches['finished_provisional']==False]
    return gw_matches

def df_to_text(event):
    event_o=old[event]['a']+old[event]['h']
    event_n=new[event]['a']+new[event]['h']
    events=[d for d in event_n if d not in event_o]
    players_with_event=[map[pl['element']].iloc[0] for pl in events]
    event_players=[]
    for player in players_with_event:
        pts=players[players['web_name']==player]['event_points'].iloc[0]
        text=emoji[event]+player
        # text+=f' [{pts} pts]'
        event_players.append(text)
    tweet_text=''
    for text in event_players:
       tweet_text+=text+'\n'

    return tweet_text

def full_time_alert(matches,num_gw):
    tweet_text='Full-Time Scores + Provisional Bonus Points System :\n'
    for index,row in matches.iterrows():
        score_h=int(row['team_h_score'])
        score_a=int(row['team_a_score'])
        team_h_short=teams_short_names[row['team_h']].iloc[0]
        team_a_short=teams_short_names[row['team_a']].iloc[0]
        match_tag=f"\n|#{team_h_short}{team_a_short} {score_h}-{score_a}\n"
        tweet_text+=match_tag
        bonus_a=row['stats'][9]['a']
        bonus_h=row['stats'][9]['h']
        d={}
        for bonus in bonus_a:
            player=bonus['element']
            player=players_names[player].iloc[0]
            bp=bonus['value']
            d[player]=bp
        for bonus in bonus_h:
            player=bonus['element']
            player=players_names[player].iloc[0]
            bp=bonus['value']
            d[player]=bp
        d = dict(sorted(d.items(), key=lambda item: item[1],reverse=True))
        for i,v in enumerate(d.items()):
            tweet_text+=v[0]+f' ({str(v[1])})\n'
            if i==2:
              break
    if(len(matches)==1):
        tweet_text+='\n\nWhat did you get from this match\n'
    else:
        tweet_text+='\n\nWhat did you get from these matches ?\n'
    tweet_text+=f'#FPL #GW{num_gw}'
    return tweet_text

def prepare_bonuses(fixtures,last_day):
    bonuses={}
    fixtures=fixtures[fixtures['day']==last_day]
    for index,row in fixtures.iterrows():
        bonus_a=row['stats'][8]['a']
        bonus_h=row['stats'][8]['h']
        d={}
        game=teams_short_names[row['team_h']].iloc[0]+teams_short_names[row['team_a']].iloc[0]
        for bonus in bonus_a:
            player=bonus['element']
            player=players_names[player].iloc[0]
            bp=bonus['value']
            d[player]=bp
        for bonus in bonus_h:
            player=bonus['element']
            player=players_names[player].iloc[0]
            bp=bonus['value']
            d[player]=bp
        bonuses[game]=d
    df = pd.DataFrame(list(bonuses.items()), columns=['game', 'bonuses'])
    df['day']=fixtures['day'].values
    return df

def df_to_bonus_text(df,current_gameweek,last_day):
    tweet_text=''
    tweet_text+=f'Gameweek {current_gameweek}, DAY {last_day}, Confirmed Bonus Points:\n\n'
    for index,row in df.iterrows():
        data=pd.DataFrame(list(row['bonuses'].items()),columns=['player','score'])
        data=data.sort_values(by='score',ascending=False)
        tweet_text+='|#'+row['game']+'\n'
        for i,r in data.iterrows():
            tweet_text+=f'{r["player"]} ({r["score"]})\n'
        tweet_text+='\n'

    tweet_text+=f'How many did you get? #FPL #GW{current_gameweek}'
    return tweet_text

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
    return tweets

def post_bonuses(tweet_text):
    bearer_token = os.getenv('BEARER_TOKEN')
    consumer_key =  os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')
    access_token = os.getenv('ACCESS_TOKEN')
    access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')
    TOKEN=os.getenv('TOKEN')
    CHANNEL_ID=os.getenv('CHANNEL_ID')
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    client = tweepy.Client(bearer_token=bearer_token, consumer_key=consumer_key, consumer_secret=consumer_secret,
                           access_token=access_token, access_token_secret=access_token_secret)
    telegram_text=tweet_text.replace('|', "")
    params = {'chat_id': CHANNEL_ID,'text': telegram_text}
    telegram = requests.post(url, params=params)
    tweets = split_text_into_tweets(tweet_text)
    last_tweet = client.create_tweet(text=tweets[0])
    print(f"Posted tweet:--------------------------------------------------------------------------------------\n{tweets[0]}")
    for tweet in tweets[1:]:
        last_tweet = client.create_tweet(text=tweet, in_reply_to_tweet_id=last_tweet.data['id'])
        print(f"Posted tweet in thread:------------------------------------------------------------------------\n{tweet}")

def post(tweet_text):
    bearer_token = os.getenv('BEARER_TOKEN')
    consumer_key =  os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')
    access_token = os.getenv('ACCESS_TOKEN')
    access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')
    TOKEN=os.getenv('TOKEN')
    CHANNEL_ID=os.getenv('CHANNEL_ID')
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'

    telegram_text=tweet_text.replace('|', "")
    params = {'chat_id': CHANNEL_ID,'text': telegram_text}
    telegram = requests.post(url, params=params)
    message_data = telegram.json()
    message_id = message_data['result']['message_id']
    message_text=message_data['result']['text']

    client = tweepy.Client(bearer_token=bearer_token, consumer_key=consumer_key, consumer_secret=consumer_secret,
                        access_token=access_token, access_token_secret=access_token_secret)
    last_tweet = client.create_tweet(text=tweet_text)
    return last_tweet,message_id,message_text

def post_reply(last_tweet,tweet_text):
    bearer_token = os.getenv('BEARER_TOKEN')
    consumer_key =  os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')
    access_token = os.getenv('ACCESS_TOKEN')
    access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')
    TOKEN=os.getenv('TOKEN')
    CHANNEL_ID=os.getenv('CHANNEL_ID')

    client = tweepy.Client(bearer_token=bearer_token, consumer_key=consumer_key, consumer_secret=consumer_secret,
                        access_token=access_token, access_token_secret=access_token_secret)
    
    tweet = client.create_tweet(text=tweet_text, in_reply_to_tweet_id=last_tweet[0].data['id'])
        
    new_message=last_tweet[3]+'\n\n'+tweet_text
    edit_params = {'chat_id': CHANNEL_ID,'message_id': last_tweet[1],'text': new_message}
    new_url = f'https://api.telegram.org/bot{TOKEN}/editMessageText'
    edit_response = requests.post(new_url, params=edit_params)
    print('edited this post\n',new_message)

def get_upcoming_games():
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

emoji={'yellow_cards':'🟨 YELLOW CARD: ','red_cards':'🟥 RED CARD: ','penalties_missed':'❌ PENALTY MISSED : ','penalties_saved':'🧤 PENALTY SAVED :','goals_scored':'⚽️ GOAL :','assists':'🅰️ Assist :','own_goals':'⚽️ OWN GOAL :'}
players=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
players_names=dict(zip(players['id'],players['web_name']))
players_names=pd.DataFrame(players_names,index=[0])
map=dict(zip(players['id'],players['web_name']))
map=pd.DataFrame(map,index=[0])
teams=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','teams')
tag=dict(zip(teams['id'],teams['short_name']))
tag=pd.DataFrame(tag,index=[0])
teams_names=dict(zip(teams['id'],teams['name']))
teams_names=pd.DataFrame(teams_names,index=[0])
teams_short_names=dict(zip(teams['id'],teams['short_name']))
teams_short_names=pd.DataFrame(teams_short_names,index=[0])

upcoming_games=get_upcoming_games()
num_gw=get_num_gw()
num_of_match=upcoming_games[-1]

# gw begins
gw_matches=prepare(num_gw)
waiting_time=gw_matches.iloc[num_of_match,-1]+200
if waiting_time>0:
    print(f'next match after {int(waiting_time/60)} mins')
    time.sleep(waiting_time)
else:
    print(f'the match has started before {-int(waiting_time/60)} mins')
last_goals,last_pen,no_assist,no_save,cnt,rc={},{},{},{},0,''
new_gw=live_gws(num_gw,upcoming_games)
# set of matches begins

while True:
    old_gw=new_gw
    time.sleep(10)
    new_gw=live_gws(num_gw,upcoming_games)

    if len(rc)>0:
        cnt+=1
        if cnt==30:
            print(rc)
            post(rc)
            cnt=0
            rc=''
    gw_ids=new_gw['id']
    print(last_goals,no_assist,rc)
    for id in gw_ids:
        last_goals.setdefault(id, None)
        no_assist.setdefault(id, False)
        last_pen.setdefault(id, None)
        no_save.setdefault(id, False)
        gw=new_gw[new_gw['id']==id]
        minute=gw['minutes'].iloc[0]
        match_tag='\n#'+tag[gw['team_h'].iloc[0]].iloc[0]+tag[gw['team_a'].iloc[0]].iloc[0]+' '+str(gw['team_h_score'].iloc[0])+'-'+str(gw['team_a_score'].iloc[0])+f' ({str(minute)}")'
        last_line=f"#FPL #GW{num_gw}"
        print('this is the current match',match_tag)

        if len(old_gw)==0 or len(new_gw)==0:
            continue
        old=prepare_stats(id,old_gw)
        new=prepare_stats(id,new_gw)
        players=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
        goals=df_to_text('goals_scored')
        assists=df_to_text('assists')
        own_goals=df_to_text('own_goals')
        pen_missed=df_to_text('penalties_missed')
        pen_saved=df_to_text('penalties_saved')
        one_rc=df_to_text('red_cards') 

        # red cards
        if len(one_rc)>0:
            one_rc+=match_tag+'\n'+last_line
            rc+=one_rc

        # goals
        if (len(goals)==0) and (len(own_goals)>0):
            goals=own_goals
        if len(goals)>0:
            if last_goals[id]!=None:
                goal_without_assist=last_goals[id]+match_tag+'\n'+last_line
                last_goals[id]=None
                print('this goal has no assist')
                print(goal_without_assist)
                post(goal_without_assist)
            wait_a_min=0
            if len(assists)>0:
                # merge goal & assist
                goal_assist=goals+assists
                goal_assist+=match_tag+'\n'+last_line
                print('goal and assist at the same time')
                print(goal_assist)
                post(goal_assist)
            else:
                # wait 1 minute
                last_goals[id]=goals
        elif len(assists)>0:
            if last_goals[id]!=None:
                if no_assist[id]==False:
                    goal_assist=last_goals[id]+assists
                    goal_assist+=match_tag+'\n'+last_line
                    last_goals[id]=None
                    print('assist came after the goal ')
                    print(goal_assist)
                    post(goal_assist)
                else:
                    no_assist[id]=False
                    assists+=match_tag+'\n'+last_line
                    print('assist in reply')
                    print(assists)
                    post_reply(last_tweet,assists)
        elif last_goals[id]!=None:
            wait_a_min+=1
            if wait_a_min==6:
                wait_a_min=0
                no_assist[id]=True
                goal_without_assist=last_goals[id]+match_tag+'\n'+last_line
                last_goals[id]=None
                print(goal_without_assist)
                last_tweet=post(goal_without_assist)

        # penalties
        if len(pen_missed)>0:
            if last_pen[id]!=None:
                pen_without_save=last_pen[id]+match_tag+'\n'+last_line
                last_pen[id]=None
                print(pen_without_save)
                post(pen_without_save)
            wait_20s=0
            if len(pen_saved)>0:
                # merge pen missed & save
                pen_missed_saved=pen_missed+'\n'+pen_saved
                pen_missed_saved+=match_tag+'\n'+last_line
                print(pen_missed_saved)
                post(pen_missed_saved)
            else:
                # wait 20s minute
                last_pen[id]=pen_missed
        elif len(pen_saved)>0:
            if last_pen[id]!=None:
                if no_save[id]==False:
                    pen_missed_saved=last_pen[id]+pen_saved
                    pen_missed_saved+=match_tag+'\n'+last_line
                    last_pen[id]=None
                    print(pen_missed_saved)
                    post(pen_missed_saved)
                else:
                    no_save[id]=False
                    pen_saved+=match_tag+'\n'+last_line
                    print(pen_saved)
                    post_reply(last_tweet_pen,pen_saved)
        elif last_pen[id]!=None:
                wait_20s+=1
                if wait_20s==2:
                    wait_20s=0
                    no_save[id]=True
                    pen_without_save=last_pen[id]+match_tag+'\n'+last_line
                    last_pen[id]=None
                    print(pen_without_save)
                    last_tweet_pen=post(pen_without_save)

    if len(new_gw)==0:
        print('full time alert of this set will be posted 15 mins later')
        time.sleep(900)
        num_of_set=get_num_of_set(num_gw,num_of_match)
        set_of_matches=current_set(num_gw,num_of_set)
        full_time_alert_text=full_time_alert(set_of_matches,num_gw)
        post_bonuses(full_time_alert_text)
        break

# set of matches ends
print(f'set of num_of_match={num_of_match} ends, confirmed Bonuses will be  after 2 hours after last match of this day ends ')
gw_matches=prepare(num_gw)

# confirmed bonuses begin
if num_of_match==len(gw_matches)-1:
    time.sleep(7200)
    last_day=gw_matches.iloc[num_of_match]['day']
    bonuses=prepare_bonuses(gw_matches,last_day)
    bonuses_text=df_to_bonus_text(bonuses,num_gw,last_day)
    print(bonuses_text)
    post_bonuses(bonuses_text)
elif gw_matches.iloc[num_of_match]['day']!=gw_matches.iloc[num_of_match+1]['day']:
    time.sleep(7200)
    last_day=gw_matches.iloc[num_of_match]['day']
    bonuses=prepare_bonuses(gw_matches,last_day)
    bonuses_text=df_to_bonus_text(bonuses,num_gw,last_day)
    print(bonuses_text)
    post_bonuses(bonuses_text)
# confirmed bonuses end

print(f'set of matches {upcoming_games} ends')
