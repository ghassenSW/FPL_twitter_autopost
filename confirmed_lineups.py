import http.client
import pandas as pd
import json
import time
import os
import requests
from collections import defaultdict
import tweepy

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

def get_id_of_match(league_id,num_gw,num_game):
    row=(num_gw-1)*10+num_game
    conn.request("GET", f"/football-get-all-matches-by-league?leagueid={league_id}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    decoded_dict = json.loads(data.decode('utf-8'))
    df=pd.DataFrame(decoded_dict['response']['matches'])
    id=int(df.iloc[row]['id'])
    return id

def get_home_lineup(match_id):
    conn.request("GET", f"/football-get-hometeam-lineup?eventid={match_id}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    decoded_dict = json.loads(data.decode('utf-8'))
    df=pd.DataFrame(decoded_dict['response'])
    if 'starters' in df.index:
      home_lineup=pd.DataFrame(df.loc['starters','lineup'])
      team_name=df.loc['name','lineup']
      return home_lineup,team_name    
    else:
      return []

def get_away_lineup(match_id):
    conn.request("GET", f"/football-get-awayteam-lineup?eventid={match_id}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    decoded_dict = json.loads(data.decode('utf-8'))
    df=pd.DataFrame(decoded_dict['response'])
    if 'starters' in df.index:
        away_lineup=pd.DataFrame(df.loc['starters','lineup'])
        team_name=df.loc['name','lineup']
        return away_lineup,team_name
    else:
       return []

def lineup_to_text(df):
  text=str(df.iloc[0,-2])+' | '
  for i in range(1,4):
    for index,row in df[df['usualPlayingPositionId']==i].iterrows():
      text+=row['lastName']+' , '
    text=text.strip(' , ')
    text+=' | '
  text=text.strip(' | ')
  return text

def make_final_text(home_team,away_team,home_lineup,away_lineup):
    home_short_name=teams_short_names[home_team]
    away_short_name=teams_short_names[away_team]
    match_tag=f'#{home_short_name}{away_short_name}\n'
    match_tag+='\n'+emoji[home_short_name]+' '
    home_lineup_text=lineup_to_text(home_lineup)
    match_tag+=home_lineup_text
    match_tag+='\n\n'+emoji[away_short_name]+' '
    away_lineup_text=lineup_to_text(away_lineup)
    match_tag+=away_lineup_text
    match_tag+=f'\n\n#FPL #GW{num_gw}'
    return match_tag

def post(tweet_text):
    bearer_token = os.getenv('BEARER_TOKEN')
    consumer_key =  os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')
    access_token = os.getenv('ACCESS_TOKEN')
    access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')
    TOKEN=os.getenv('TOKEN')
    CHANNEL_ID=os.getenv('CHANNEL_ID')
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'

    params = {'chat_id': CHANNEL_ID,'text': text}
    telegram = requests.post(url, params=params)

    client = tweepy.Client(bearer_token=bearer_token, consumer_key=consumer_key, consumer_secret=consumer_secret,
                        access_token=access_token, access_token_secret=access_token_secret)
    last_tweet = client.create_tweet(text=text)


teams_short_names={'Arsenal':'ARS','Chelsea':'CHE','Brentford':'BRE','AFC Bournemouth':'BOU','Crystal Palace':'CRY','Fulham':'FUL','West Ham United':'WHU','Everton':'EVE','Wolverhampton Wanderers':'WOL','Southampton':'SOU','Brighton & Hove Albion':'BHA','Manchester City':'MCI','Liverpool':'LIV','Aston Villa':'AVL','Manchester United':'MUN','Leicester City':'LEI','Nottingham Forest':'NFO','Newcastle United':'NEW','Tottenham Hotspur':'TOT','Ipswich Town':'IPS'}

emoji={'ARS': '🔫', 'AVL': '🦁', 'BOU': '🍒', 'BRE': '🐝', 'BHA': '🕊', 'CHE': '🔵', 'CRY': '🦅', 'EVE': '🍬', 'FUL': '⚪️', 'IPS': '🚜', 'LEI': '🦊', 'LIV': '🔴', 'MCI': '🌑', 'MUN': '👹', 'NEW': '⚫️', 'NFO': '🌳', 'SOU': '😇', 'TOT': '🐓', 'WHU': '⚒️', 'WOL': '🐺'}

conn = http.client.HTTPSConnection("free-api-live-football-data.p.rapidapi.com")
X_RAPIDAPI_KEY=os.getenv('X_RAPIDAPI_KEY')
headers = {
    'x-rapidapi-key': X_RAPIDAPI_KEY,
    'x-rapidapi-host': "free-api-live-football-data.p.rapidapi.com"
}

num_gw=get_num_gw()-1
new_games=get_new_games()
for game in new_games:
    match_id=get_id_of_match(47,num_gw,game)
    home_lineup,home_team=get_home_lineup(match_id)
    away_lineup,away_team=get_away_lineup(match_id)
    if (len(home_lineup)==0) or (len(away_lineup)==0):
       continue
    text=make_final_text(home_team,away_team,home_lineup,away_lineup)
    post(text)
    break
    
