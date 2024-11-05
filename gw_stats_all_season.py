import requests
import numpy as np
import pandas as pd
import time
import tweepy
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

def prepare_def(num_gameweeks):
    players=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
    goalkeepers=players[['web_name','team','element_type','id','goals_conceded','expected_goals_conceded']]
    goalkeepers=goalkeepers[players['element_type']==1]
    goalkeepers=goalkeepers.drop('element_type',axis=1)
    teams=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','teams')
    teams=teams[['id','name']]

    all_fixtures=url_to_df('https://fantasy.premierleague.com/api/fixtures/')

    stats = pd.DataFrame(np.zeros((num_gameweeks*20, 4)), dtype='int')
    stats.columns = ['team', 'gameweek', 'goals_conceded', 'expected_goals_conceded']
    li=[]
    for i in range(1,num_gameweeks+1):
        li.extend([i]*20)
    stats['gameweek']=li
    stats['expected_goals_conceded']=stats['expected_goals_conceded'].astype(float)
    for i in range(1,num_gameweeks+1):
        stats.loc[stats['gameweek']==i,'team']=range(1,21)
    stats['team_name']=''
    for index,row in stats.iterrows():
        stats.iloc[index,-1]=teams.iloc[row['team']-1,1]

    for index,row in goalkeepers.iterrows():
        id=row['id']
        url=f'https://fantasy.premierleague.com/api/element-summary/{id}/'
        gk=url_to_df(url,'history')
        gk=gk[['element','opponent_team','goals_conceded','expected_goals_conceded']]
        gk['expected_goals_conceded']=gk['expected_goals_conceded'].astype(float)
        gk.loc[:,'gameweek']=gk.index+1
        gk.loc[:,'team_id']=''
        for index,row in gk.iterrows():
            fixtures=all_fixtures[['event','team_h','team_a']]
            fixtures=fixtures[fixtures['event']==row['gameweek']]
            ligne=fixtures[(fixtures['team_h']==row['opponent_team']) | (fixtures['team_a']==row['opponent_team'])]
            gk.iloc[index,5]=ligne.iloc[0,2]+ligne.iloc[0,1]-row['opponent_team']
        for index,row in gk.iterrows():
            sel=stats[stats.loc[:,'gameweek']==row['gameweek']]
            sel=sel[sel.loc[:,'team']==row['team_id']]
            ind=sel.index.item()
            stats.iloc[ind,2]+=row['goals_conceded']
            stats.iloc[ind,3]+=row['expected_goals_conceded']
    stats=stats.drop('team_name',axis=1)
    stats=stats.groupby('team')[['goals_conceded','expected_goals_conceded']].sum()
    stats.index=list(df.values())
    stats=stats.sort_values(by='goals_conceded',ascending=True)
    stats['expected_goals_conceded']=stats['expected_goals_conceded'].round(2)

    top=stats.iloc[:10,:]
    bottom=stats.iloc[-10:,:]
    bottom=bottom.sort_values(by=['goals_conceded','expected_goals_conceded'],ascending=False)
    return top,bottom

def df_to_text_atk(df,word,num_gameweeks):
  text=f'#FPL #GW{num_gameweeks+1} , {word} 10 - TEAMS - GOALS (xG) [All Season]\n'
  for i,row in df.iterrows():
    g=row['goals_scored'].astype(int)
    xg=row['expected_goals']
    text+=f'\n{i}: {g} ({xg})'
  return text

def df_to_text_def(df,word,num_gameweeks):
  text=f'#FPL #GW{num_gameweeks+1} , {word} 10 - TEAMS - GOALS CONCEDED (xGC) [All Season]\n'
  for i,row in df.iterrows():
    gc=row['goals_conceded'].astype(int)
    xgc=row['expected_goals_conceded']
    text+=f'\n{i}: {gc} ({xgc})'
  return text

def post(tweet_text):
    bearer_token = "AAAAAAAAAAAAAAAAAAAAAHpZwQEAAAAAa%2BL2Fn26r7fRpOz6okyMP4gT8cI%3DgH6vulMQnvuTNGNywG06fnGEiuuYD28RHt8nf4wDzeP8DLJRJy"
    consumer_key = "5H7fUfbrQ2XF5WqSG67ttM2R1"
    consumer_secret = "Bw1MR5iPieCLgzodClVRjWIaPVrIPk7r7bif9t261WbgqiGob0"
    access_token = "1844404415349817349-41SFbOP4Fmw7ptB4Jhgi52NQtn2l1V"
    access_token_secret = "mrWXSuAUgvq9riop7xnO1mJ7XNPCdc4ZwZmjv4zmttdEJ"
    TOKEN='7187953343:AAFSZ7I0FzzsQes_SrhG2dX74IRIcLgAa54'
    CHANNEL_ID='-1001534852752'
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
bottom_text_atk=df_to_text_atk(bottom_atk,'BOTTOM',num_gw)

top_def,bottom_def=prepare_def(num_gw)
top_text_def=df_to_text_def(top_def,'TOP',num_gw)
bottom_text_def=df_to_text_def(bottom_def,'BOTTOM',num_gw)

post(top_text_atk)
time.sleep(7200)
post(bottom_text_atk)
time.sleep(7200)
post(top_text_def)
time.sleep(7200)
post(bottom_text_def)
print(f'posted after gw{num_gw}')
