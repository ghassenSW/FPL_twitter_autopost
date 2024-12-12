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
from pymongo import MongoClient



sys.path.append('./src')
fb = sfc.FBref()
sc = sfc.Sofascore()

def fb_to_sc(year_fb):
    year_sc=year_fb[2:4]+'/'+year_fb[-2:]
    return year_sc

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

MONGODB_URI=os.getenv('MONGODB_URI')
client = MongoClient(MONGODB_URI)
db = client['my_database']
collection = db['fpl_data']
teams_stats_db=db['teams_stats']

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_NAME = 'ghassenSW/FPL_twitter_autopost'
FILE_PATH = 'teams_data_from_2017.xlsx'

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

file_content = repo.get_contents(FILE_PATH)
decoded_content = base64.b64decode(file_content.content)

excel_data = io.BytesIO(decoded_content)
df = pd.read_excel(excel_data, sheet_name=None)


year_fb=list(df.keys())[-1]
year_sc=fb_to_sc(year_fb)
events=sc.get_match_dicts(year_sc,'EPL')
new_sheet=[]
for event in events:
  id=event['id']
  try:
    stats=prepare_sc(id)
    column_types = {
        "GW": "int",
        "team H": "string",
        "team A": "string",
        "Goals H": "int",
        "Goals A": "int",
        "xG H": "float",
        "xG A": "float",
        "Shots H": "int",
        "Shots A": "int",
        "SiB H": "int",
        "SiB A": "int",
        "SoT H": "int",
        "SoT A": "int",
        "BC H": "int",
        "BC A": "int",
    }
    stats = stats.astype(column_types)
    new_sheet.append(stats)
  except Exception as e:
    continue
avl_mun = {
    "GW": [7],
    "team H": ["Aston Villa"],
    "team A": ["Manchester United"],
    "Goals H": [0],
    "Goals A": [0],
    "xG H": [0.5],
    "xG A": [0.56],
    "Shots H": [11],
    "Shots A": [10],
    "SiB H": [6],
    "SiB A": [4],
    "SoT H": [1],
    "SoT A": [4],
    "BC H": [1],
    "BC A": [4],
}
avl_mun_df=pd.DataFrame(avl_mun)
new_sheet.append(avl_mun_df)
new_sheet=pd.concat(new_sheet)
new_sheet=new_sheet.sort_values(['GW'])
df[year_fb]=new_sheet

data=df[year_fb]
data.reset_index(inplace=True)
records = data.to_dict(orient='records')
teams_stats_db.delete_many({})
teams_stats_db.insert_many(records)
excel_buffer = io.BytesIO()

with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
    for sheet_name, sheet in df.items():
        sheet.to_excel(writer, sheet_name=sheet_name, index=False)
try:
    file_content = repo.get_contents(FILE_PATH)
    sha = file_content.sha
    excel_buffer.seek(0)
    repo.update_file(FILE_PATH, "Overwriting Excel file with updated data", excel_buffer.read(), sha)
    print(f"File {FILE_PATH} has been updated.")
except Exception as e:
    repo.create_file(FILE_PATH, "Adding new Excel file", excel_buffer.read())
    print(f"File {FILE_PATH} has been created.")
