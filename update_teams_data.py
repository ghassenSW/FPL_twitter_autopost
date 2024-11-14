import os
import io
from github import Github
import pandas as pd
import numpy as np
import base64
import requests
import tweepy
import time
from datetime import datetime
import sys
import ScraperFC as sfc


sys.path.append('./src')
fb = sfc.FBref()
sc = sfc.Sofascore()

def prepare_sc(match_id):
  matchy=sc.get_match_dict(match_id)
  matchy={'event':matchy}
  matchy=pd.DataFrame(matchy)
  score=matchy.loc[['homeScore','awayScore']]
  score.iloc[0,0]=score.iloc[0,0]['normaltime']
  score.iloc[1,0]=score.iloc[1,0]['normaltime']
  score.index=['home','away']
  score.columns=['Goals']
  teams=matchy.loc[['homeTeam','awayTeam']]
  teams.iloc[0,0]=teams.iloc[0,0]['name']
  teams.iloc[1,0]=teams.iloc[1,0]['name']
  teams.index=['home','away']
  teams.columns=['team']

  stats=sc.scrape_team_match_stats(match_id)
  stats=stats.T
  stats.columns=stats.iloc[0]
  stats=stats.drop(['name'],axis=0)
  stats=stats[['Expected goals','Total shots','Shots inside box','Shots on target','Big chances']]
  stats=stats.T
  stats=stats[stats['period']=='ALL']
  stats=stats.T
  stats.columns=['xG','Shots','Total_shots','SiB','SoT','BC']
  stats=stats.drop(['Total_shots'],axis=1)
  stats=stats.loc[['home','away']]
  stats=pd.concat([teams,score,stats],axis=1)

  num_gw=matchy.loc['roundInfo'].iloc[0]['round']
  num_season=matchy.loc['season'].iloc[0]['year']
  stats.index=['H','A']
  df=pd.DataFrame({'season':[num_season],'GW':[num_gw]})
  df.index=df['season']
  df=df.drop(['season'],axis=1)
  for col in stats.columns:
    for index,row in stats.iterrows():
      new_col=col+' '+index
      new_df={new_col:[row[col]]}
      new_df=pd.DataFrame(new_df)
      new_df.index=df.index
      df=pd.concat([df,pd.DataFrame(new_df)],axis=1)
  return df

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_NAME = 'ghassenSW/FPL_twitter_autopost'
FILE_PATH = 'teams_data_from_2017.xlsx'

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

file_content = repo.get_contents(FILE_PATH)
decoded_content = base64.b64decode(file_content.content)

excel_data = io.BytesIO(decoded_content)
df = pd.read_excel(excel_data, sheet_name=None)


year_sc=list(df.keys())[-1]
events=sc.get_match_dicts(year_sc,'EPL')
all_stats=[]
for event in events:
  id=event['id']
  try:
    stats=prepare_sc(id)
    all_stats.append(stats)
  except Exception as e:
    continue
all_stats=pd.concat(all_stats)
all_stats=all_stats.sort_values(['GW'])
df[year_sc]=all_stats


print(df[year_sc])
print("File updated and pushed successfully!")
