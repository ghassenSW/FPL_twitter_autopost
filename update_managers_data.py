import pandas as pd
import requests
from predict_results import predict
import os 
from pymongo import MongoClient

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

try:
  from dotenv import load_dotenv
  load_dotenv()
  MONGODB_URI=os.getenv('MONGODB_URI')
except Exception as e:
  try:
    MONGODB_URI=os.environ.get('MONGODB_URI')
  except Exception as e2:
    print(e2)

client = MongoClient(MONGODB_URI)
db = client['my_database']
collection = db['fpl_data']
managers_stats_db=db['managers_stats']

num_gw=get_num_gw()
managers=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','elements')
managers=managers[managers['element_type']==5]
team_manager=dict(zip(managers['team'],managers['web_name']))
teams=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','teams')
id_team=dict(zip(teams['id'],teams['short_name']))
team_position=dict(zip(teams['id'],teams['position']))

df=teams[['name','position','id']]
df = df.copy()
df['manager'] = df['id'].map(team_manager)
teams_table=df.to_dict(orient="index")
teams_table=[v for k,v in teams_table.items()]
for team_dict in teams_table:
  matches=url_to_df('https://fantasy.premierleague.com/api/fixtures/?future=1')
  matches=matches[(matches['team_a']==team_dict['id']) | (matches['team_h']==team_dict['id'])][['team_a','team_h']]
  matches['opp_team']=matches['team_a']+matches['team_h']-team_dict['id']
  team_dict['fix']=([{str(id_team[x]): team_position[x]} for x in matches['opp_team']])
  team_dict['result']=([predict(num_gw+i+1,team_dict['id'],id_team[x],team_dict['position']>=team_position[x]+5) for i,x in enumerate(matches['opp_team'])])

managers_stats_db.delete_many({})
managers_stats_db.insert_many(teams_table)
