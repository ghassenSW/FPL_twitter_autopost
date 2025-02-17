import joblib
import pandas as pd
import requests
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
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

def match_outcome(row):
    if row['Goals H'] > row['Goals A']:
        return 1  # Home team wins
    elif row['Goals H'] < row['Goals A']:
        return 0  # Away team wins
    else:
        return 2  # Draw



tag_team={'ARS': 'Arsenal', 'CHE': 'Chelsea', 'BRE': 'Brentford', 'BOU': 'Bournemouth', 'CRY': 'Crystal Palace', 'FUL': 'Fulham', 'WHU': 'West Ham United', 'EVE': 'Everton', 'WOL': 'Wolverhampton', 'SOU': 'Southampton', 'BHA': 'Brighton & Hove Albion', 'MCI': 'Manchester City', 'LIV': 'Liverpool', 'AVL': 'Aston Villa', 'MUN': 'Manchester United', 'LEI': 'Leicester City', 'NFO': 'Nottingham Forest', 'NEW': 'Newcastle United', 'TOT': 'Tottenham Hotspur', 'IPS': 'Ipswich Town'}

teams_db={'Arsenal': 'Arsenal', 'Chelsea': 'Chelsea', 'Brentford': 'Brentford', 'Bournemouth': 'Bournemouth', 'Crystal Palace': 'Crystal Palace', 'Fulham': 'Fulham', 'West Ham': 'West Ham United', 'Everton': 'Everton', 'Wolves': 'Wolverhampton', 'Southampton': 'Southampton', 'Brighton': 'Brighton & Hove Albion', 'Man City': 'Manchester City', 'Liverpool': 'Liverpool', 'Aston Villa': 'Aston Villa', 'Man Utd': 'Manchester United', 'Leicester': 'Leicester City', "Nott'm Forest": 'Nottingham Forest', 'Newcastle': 'Newcastle United', 'Spurs': 'Tottenham Hotspur', 'Ipswich': 'Ipswich Town'}


try:
  from dotenv import load_dotenv
  load_dotenv()
  MONGODB_URI=os.getenv('MONGODB_URI')
except Exception as e:
  try:
    MONGODB_URI=os.environ.get('MONGODB_URI')
  except Exception as e2:
    print(e2)

def predict(num_gw,team,opp,ok):
  client = MongoClient(MONGODB_URI)
  db = client['my_database']
  collection = db['fpl_data']
  teams_stats_db=db['teams_stats']
  stats=list(teams_stats_db.find())
  df=pd.DataFrame(stats)
  df['Outcome'] = df.apply(match_outcome, axis=1)

  team_id=dict(zip(sorted(df['team H'].unique()),range(1,21)))
  teams_names=list(team_id.keys())
  teams=url_to_df('https://fantasy.premierleague.com/api/bootstrap-static/','teams')
  teams=teams[['id','position','strength','strength_overall_home',"strength_overall_away","strength_attack_home","strength_attack_away","strength_defence_home",'strength_defence_away']]
  teams_home=teams.copy()
  teams_away=teams.copy()
  teams_away.columns=['id A','position A','strength A','strength_overall_home A',"strength_overall_away A","strength_attack_home A","strength_attack_away A","strength_defence_home A",'strength_defence_away A']
  teams_home.columns=['id H','position H','strength H','strength_overall_home H',"strength_overall_away H","strength_attack_home H","strength_attack_away H","strength_defence_home H",'strength_defence_away H']

  df['id H']=df['team H'].map(team_id)
  df['id A']=df['team A'].map(team_id)
  df=df[['GW','id H','id A','Outcome']]

  df = df.merge(teams_home, on="id H", how="left")
  df = df.merge(teams_away, on="id A", how="left")

  X = df[['GW','id A','position A','strength A','strength_overall_home A',"strength_overall_away A","strength_attack_home A","strength_attack_away A","strength_defence_home A",'strength_defence_away A','id H','position H','strength H','strength_overall_home H',"strength_overall_away H","strength_attack_home H","strength_attack_away H","strength_defence_home H",'strength_defence_away H']]
  y = df['Outcome']
  X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
  scaler = StandardScaler()
  X_train = scaler.fit_transform(X_train)
  X_test = scaler.transform(X_test)
  # Initialize Logistic Regression
  model = LogisticRegression(max_iter=1000)

  # Train the model
  model.fit(X_train, y_train)

  # Predict probabilities for each class (Win, Loss, Draw)
  y_pred_proba = model.predict_proba(X_test)

  y_pred = model.predict(X_test)
  new_match = pd.DataFrame({
      'GW': [num_gw],
      'id H': [team],
      'id A': [team_id[tag_team[opp]]]
  }, index=[0]) # Added index to avoid warning

  new_match = new_match.merge(teams_home, on="id H", how="left")
  new_match = new_match.merge(teams_away, on="id A", how="left")
  new_match= new_match[['GW','id A','position A','strength A','strength_overall_home A',"strength_overall_away A","strength_attack_home A","strength_attack_away A","strength_defence_home A",'strength_defence_away A','id H','position H','strength H','strength_overall_home H',"strength_overall_away H","strength_attack_home H","strength_attack_away H","strength_defence_home H",'strength_defence_away H']]
  new_match_scaled = scaler.transform(new_match)

  # Predict probability
  win_probability = model.predict_proba(new_match_scaled)[0]
  result=np.argmax(win_probability)
  score=0
  if result==1:
     score+=6
     if ok:
        score+=10
  elif result==2:
     score+=3
     if ok:
        score+=5
  return score 
