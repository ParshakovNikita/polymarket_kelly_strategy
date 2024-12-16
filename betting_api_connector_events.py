import requests
import json
import pandas as pd
from datetime import datetime
import os


class Bet_API():

    def __init__(self, path_to_args, league) -> None:

        self.name = 'BettingAPI'
        with open(path_to_args, 'r', encoding='utf-8') as json_file:
            private_kargs = json.load(json_file)
        self.api_params = private_kargs['betting_api_params']

        self.SPORT = self.api_params["SPORT"][league] # https://the-odds-api.com/sports-odds-data/sports-apis.html
        # self.event_name = os.path.splitext(os.path.basename(private_kargs['path_to_html']))[0]
        self.league = league
        self.API_KEY = self.api_params['API_KEY']
        self.REGIONS = self.api_params['REGIONS']
        self.MARKETS = self.api_params['MARKETS']
        self.ODDS_FORMAT = self.api_params['ODDS_FORMAT']
        self.DATE_FORMAT = self.api_params['DATE_FORMAT']
        self.probs = pd.DataFrame()
        self.probs_df = pd.DataFrame()
        self.update_probs()
        self.dump_results()


    def update_probs(self) -> None:
        # url = f'https://api.the-odds-api.com//v4/sports/{SPORT}/odds/?apiKey={API_KEY}&regions={REGIONS}'
        try:
            odds_response = requests.get(
                f'https://api.the-odds-api.com/v4/sports/{self.SPORT}/odds',
                params={
                    'api_key': self.API_KEY,
                    'regions': self.REGIONS,
                    'markets': self.MARKETS,
                    'oddsFormat': self.ODDS_FORMAT,
                    'dateFormat': self.DATE_FORMAT,
                }
            )
            if odds_response.status_code != 200:
                print(f'Failed to get odds: status_code {odds_response.status_code}, response body {odds_response.text}')
            else:
                odds_json = odds_response.json()
                if not odds_json:
                    print('Received empty odds response from API')
                    return None
                self.probs = self.json_to_df(odds_json)
                if not os.path.exists(f'database/{self.league}/probs'):
                    os.makedirs(f'database/{self.league}/probs')
                self.probs.to_csv(f'database/{self.league}/probs/{self.league}_probs_{datetime.now().date()}_{datetime.now().hour}.csv', index_label=False) # maybe move to polymarket_lib

                print('Remaining requests', odds_response.headers['x-requests-remaining'])
                print('Used requests', odds_response.headers['x-requests-used'])
        except Exception as e:
            print("betting API update_odds func error", e)
        
        return None
    
    def dump_results(self):
        directory = f'database/{self.league}/results/'
        if not os.path.exists(directory):
            os.makedirs(directory)
        today = datetime.now().strftime('%Y-%m-%d')
        files = os.listdir(directory)
        if not files:
            print("Empty dir, collecting results")
            self.collect_results()
        else:
            if not any(today in f for f in files):
                self.collect_results()
                
        return None
    
    def collect_results(self):
        url = f'https://api.the-odds-api.com/v4/sports/{self.SPORT}/scores/?daysFrom=3&apiKey={self.API_KEY}'
        try:
            odds_response = requests.get(url)
            if odds_response.status_code != 200:
                print(f'Failed to get odds: status_code {odds_response.status_code}, response body {odds_response.text}')
            else:
                odds_json = odds_response.json()
                if not odds_json:
                    print('Received empty odds response from API')
                    return None
                
                data_list = []
                for match in odds_json:
                    if match['scores'] != None:
                        if self.league == 'NFL':
                            data_list.append({
                                'match_id': match['id'],
                                'league': match['sport_title'],
                                'commence_time': match['commence_time'],
                                'home_team': match['home_team'],
                                'away_team': match['away_team'],
                                'home_team_score': int(match['scores'][1]['score']),
                                'away_team_score': int(match['scores'][0]['score'])         
                            })
                        else:
                            data_list.append({
                                'match_id': match['id'],
                                'league': match['sport_title'],
                                'commence_time': match['commence_time'],
                                'home_team': match['home_team'],
                                'away_team': match['away_team'],
                                'home_team_score': int(match['scores'][0]['score']),
                                'away_team_score': int(match['scores'][1]['score'])         
                            })                            
                if len(data_list) > 0:
                    df = pd.DataFrame(data_list)
                    df['commence_time'] = pd.to_datetime(df['commence_time']).dt.floor('H')
                    if not os.path.exists(f'database/{self.league}/results'):
                        os.makedirs(f'database/{self.league}/results')
                    df.to_csv(f'database/{self.league}/results/{self.league}_results_{datetime.now().date()}.csv', index_label=False) # maybe move to polymarket_lib
                else:
                    print('No results to update', self.league)
                print('Remaining requests', odds_response.headers['x-requests-remaining'])
                print('Used requests', odds_response.headers['x-requests-used'])
        except Exception as e:
            print("betting API collect_results func error", e)
        return None
    

    def json_to_df(self, json_response) -> pd.DataFrame:
        avg_probs = []

        # bookmaker_blacklist = ['Matchbook', 'Betfair']
        
        for match in json_response:
            match_id = match['id']
            commence_time = match['commence_time']  # Преобразуем дату в формат datetime
            
            for bookmaker in match['bookmakers']:
                # if bookmaker['title'] in bookmaker_blacklist:
                #     continue
                margin_list = []
                for outcome in bookmaker['markets'][0]['outcomes']:
                    margin_list.append(1/outcome['price'])
                margin = sum(margin_list)
                for outcome in bookmaker['markets'][0]['outcomes']:
                    avg_probs.append({
                        'league': self.league,
                        'match_id': match_id,
                        'commence_time': commence_time,
                        'outcome': outcome['name'],
                        'bookmaker': bookmaker['title'],
                        'prob': 1/(outcome['price']*margin)
                    })
        
        self.probs_df = pd.DataFrame(avg_probs)
        self.probs_df['commence_time'] = pd.to_datetime(self.probs_df['commence_time']).dt.floor('H')
        probs_result = self.probs_df.groupby(by=['match_id','commence_time','outcome']).agg({
                                                              'prob': ['mean', 'min', 'max', 'std', 'count']
                                                              })
        probs_result = probs_result.sort_index(level='commence_time')
        return probs_result['prob']