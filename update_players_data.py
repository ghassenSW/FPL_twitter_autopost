import requests
import numpy as np
import pandas as pd
import tweepy
from datetime import datetime,timedelta
from collections import defaultdict
import json
import time
import os
from fuzzywuzzy import fuzz
from scipy.optimize import linear_sum_assignment
from pymongo import MongoClient

import sys
import ScraperFC as sfc

sys.path.append('./src')
sc = sfc.Sofascore()

try:
  MONGODB_URI=os.getenv('MONGODB_URI')
except Exception as e:
  try:
    MONGODB_URI=os.environ.get('MONGODB_URI')
  except Exception as e2:
    print(e2)

client = MongoClient(MONGODB_URI)
db = client['my_database']
collection = db['fpl_data']
players_stats_db=db['players_stats']

def position_func(n):
  if n==1:
    return 'GKP'
  elif n==2:
    return 'DEF'
  elif n==3:
    return 'MID'
  elif n==4:
    return 'FWD'

def mapping(list_a, list_b):
    if len(list_a) != len(list_b):
        raise ValueError("Both lists must have the same length in ")
    n = len(list_a)
    similarity_matrix = np.zeros((n, n))
    for i, a in enumerate(list_a):
        for j, b in enumerate(list_b):
            similarity_matrix[i, j] = fuzz.ratio(a, b)
    cost_matrix = 100 - similarity_matrix
    row_indices, col_indices = linear_sum_assignment(cost_matrix)
    matched_pairs = {}
    for i, j in zip(row_indices, col_indices):
      matched_pairs[list_a[i]]=list_b[j]
    return matched_pairs

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
    events=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','events')
    num_gw=len(events[events['finished']==True])+1
    return num_gw

def get_player_team(round,opp_team):
  fixtures=url_to_df('https://fantasy.premierleague.com/api/fixtures/?future=0')
  fixtures=fixtures[['event','team_a','team_h']].copy()
  fixtures['team_a'] = fixtures['team_a'].apply(lambda x: fpl_teams[x-1])
  fixtures['team_h'] = fixtures['team_h'].apply(lambda x: fpl_teams[x-1])
  fixtures=fixtures[fixtures['event']==round].copy()
  fixtures=fixtures[(fixtures['team_a']==opp_team) | (fixtures['team_h']==opp_team)]
  if fixtures['team_a'].iloc[0]==opp_team:
    return fixtures['team_h'].iloc[0]
  else:
    return fixtures['team_a'].iloc[0]

teams_short_names={'Arsenal':'ARS','Chelsea':'CHE','Brentford':'BRE','Bournemouth':'BOU','Crystal Palace':'CRY','Fulham':'FUL','West Ham United':'WHU','Everton':'EVE','Wolverhampton':'WOL','Southampton':'SOU','Brighton & Hove Albion':'BHA','Manchester City':'MCI','Liverpool':'LIV','Aston Villa':'AVL','Manchester United':'MUN','Leicester City':'LEI','Nottingham Forest':'NFO','Newcastle United':'NEW','Tottenham Hotspur':'TOT','Ipswich Town':'IPS','Burnley':'BUR','Luton Town':'LUT','Sheffield United':'SHU'}

# get all the teams in sc 
year_sc='24/25'
events=sc.get_match_dicts(year_sc,'EPL')
sc_teams=set()
for event in events:
  match_id=event['id']
  teams=sc.get_team_names(match_id)
  for team in teams:
    sc_teams.add(team)
    if(len(sc_teams)>=20):
        break
sc_teams=list(sc_teams)

# mapping sc teams to fpl
teams=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','teams')
fpl_teams=list(teams['name'])
teams_sc_fpl=mapping(sc_teams,fpl_teams)


# fill the all_stats with sc data
all_stats=[]
players_by_match={}
cols=['bigChanceMissed','goals','bigChanceCreated','blockedScoringAttempt','onTargetScoringAttempt','ownGoals','hitWoodwork','total_cross']
for event in events: #380 events
  id=event['id']
  num_gw=event['roundInfo']['round']
  sc_stats=sc.scrape_player_match_stats(id)
  teams=sc.get_team_names(id)
  sc_stats['opp_team']=sc_stats['teamName'].apply(lambda x:teams[0] if x==teams[1] else teams[1])
  sc_stats['num_gw']=num_gw
  sc_stats=sc_stats.fillna(0)
  match_tag=teams_short_names[event['homeTeam']['name']]+teams_short_names[event['awayTeam']['name']]
  sc_stats['match_tag']=match_tag
  sc_stats['season']=year_sc
  sc_stats['H/A']=sc_stats['opp_team'].apply(lambda x: 'A' if x==event['homeTeam']['name'] else 'H')
  sc_stats['teamName']=sc_stats['teamName'].apply(lambda x:teams_sc_fpl[x])
  sc_stats['opp_team']=sc_stats['opp_team'].apply(lambda x:teams_sc_fpl[x])
  try:
    for col in cols:
      if(col not in sc_stats.columns):
        sc_stats[col]=0
    sc_stats=sc_stats[sc_stats['minutesPlayed']>0]
    sc_stats['shots']=sc_stats['shotOffTarget']+sc_stats['blockedScoringAttempt']+sc_stats['onTargetScoringAttempt']
    sc_stats=sc_stats[['season','num_gw','name','teamName','opp_team','H/A','match_tag','minutesPlayed','goals','expectedGoals','goalAssist','expectedAssists','ownGoals','shots','bigChanceMissed','keyPass','bigChanceCreated','onTargetScoringAttempt','hitWoodwork','totalCross']]
    sc_stats.columns=['season','num_gw','full_name','team','opp_team','H/A','tag','minutes_played','goals','xG','assists','xA','OG','shots','bc','chances_created','bc_created','sot','hit_wood_work','total_cross']
    all_stats.append(sc_stats)
  except Exception as e:
    print(match_tag,':',e)
    continue
all_stats=pd.concat(all_stats)
all_stats=all_stats.sort_values(['num_gw'])


# get team player in sc
team_players_sc={}
for team in fpl_teams:
  stats=all_stats[all_stats['team']==team]
  players_sc=list(set(stats['full_name']))
  team_players_sc[team]=players_sc

# get team players in fpl
team_players_fpl={}
players=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
players['team']=players['team'].apply(lambda x:fpl_teams[x-1])
players['full_name']=players['first_name']+' '+players['second_name']
players_id=dict(zip(players['id'],players['full_name']))
id_web_name=dict(zip(players['id'],players['web_name']))
players['element_type']=players['element_type'].apply(lambda x:position_func(x))
id_position=dict(zip(players['id'],players['element_type']))
ids=players['id']
for id in ids:
  player=url_to_df(f'https://fantasy.premierleague.com/api/element-summary/{id}/','history')
  player=player[player['minutes']>0]
  if len(player)>0:
    player_name=players_id[id]
    for index,row in player.iterrows():
      player_team=get_player_team(row['round'],fpl_teams[row['opponent_team']-1])
      team_players_fpl.setdefault(player_team, set()).add(player_name)

# mapping sc players to fpl 
sc_fpl_players={}
for team in fpl_teams:
  sc_fpl_players.update(mapping(team_players_sc[team],list(team_players_fpl[team])))

all_stats['full_name']=all_stats['full_name'].apply(lambda x:sc_fpl_players[x])

# update the assists to fpl ones
for id in ids:
  player=url_to_df(f'https://fantasy.premierleague.com/api/element-summary/{id}/','history')
  player=player[player['minutes']>0]
  player_name=players_id[id]
  web_name=id_web_name[id]
  position=id_position[id]
  if len(player)>0:
    for index,row in player.iterrows():
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'assists']=row['assists']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'web_name']=web_name
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'id']=id
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'position']=position
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'total_points']=row['total_points']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'kickoff_time']=row['kickoff_time']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'penalties_saved']=row['penalties_saved']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'penalties_missed']=row['penalties_missed']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'CS']=row['clean_sheets']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'goals_conceded']=row['goals_conceded']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'yellow_cards']=row['yellow_cards']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'red_cards']=row['red_cards']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'saves']=row['saves']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'bonus']=row['bonus']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'bps']=row['bps']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'value']=row['value']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'transfers_in']=row['transfers_in']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'transfers_out']=row['transfers_out']
      all_stats.loc[(all_stats['full_name']==player_name) & (all_stats['num_gw']==row['round']),'selected']=row['selected']

records = all_stats.to_dict(orient='records')
for record in records:
  exists=players_stats_db.find_one(record)
  if not exists:
    players_stats_db.insert_one(record)
