
import os
import pandas as pd
from polymarket_connector import Polymarket_connector, Market
from database import Database
from betting_api_connector_events import Bet_API
from datetime import datetime, timedelta

class Polymarket_events:

    def __init__(self, path_to_args, league):
        self.name = 'Polymarket_MM'
        self.path_to_args = path_to_args
        self.league = league

        self.polymarket_connector = Polymarket_connector(path_to_args)
        self.database = Database(path_to_args, league)
        self.condition_ids = self.database.read_condition_ids()
        self.bet_api = Bet_API(path_to_args, league)

        self.markets = []
        for id in self.condition_ids:
            market = Market(self.polymarket_connector.client, id, league)
            if market.status == 1:
                self.markets.append(market)
        self.last_update_markets = datetime.now()
        self.poly_prices = pd.DataFrame(columns=['league', 'question', 'commence_time', 'team', 'best_bid', 'best_ask'])
        if self.markets:
            self.agg_markets_to_df()
        else:
            print('Get empty prices from polymarket')
        print('Polymarket_MM ready to make money!')


    def agg_markets_to_df(self):
        data_list = []

        for market in self.markets:
            data_list.append(
                {'league': market.league,
                'question': market.question,
                'commence_time': market.game_start_time,
                'team': market.team_0_outcome,
                'best_bid': float(market.team_0_best_bid.price),
                'best_ask': float(market.team_0_best_ask.price)
                    })
            data_list.append(
                {'league': market.league,
                 'question': market.question,
                'commence_time': market.game_start_time,
                'team': market.team_1_outcome,
                'best_bid': float(market.team_1_best_bid.price),
                'best_ask': float(market.team_1_best_ask.price)
                    })
            
        df = pd.DataFrame(data_list)
        df['commence_time'] = pd.to_datetime(df['commence_time']).dt.floor('H')
        self.poly_prices = df
    
    def run_signal(self) -> pd.DataFrame:
        probs = self.bet_api.probs.reset_index()
        map_table = self.database.map_table
        poly_prices = self.poly_prices.copy()
        replacement_dict = map_table.to_dict()
        poly_prices['team'] = poly_prices['team'].replace(replacement_dict['bet_api_team_name'])
        poly_prices.rename(columns={'team': 'outcome'}, inplace=True)
        merged_df = pd.merge(poly_prices, probs, on=['commence_time', 'outcome'], how='inner')
        merged_df = merged_df.sort_values(by=['commence_time', 'question'])
        merged_df = merged_df.set_index(['question', 'commence_time', 'outcome'])
        # merged_df = merged_df.drop(columns=['match_id'])
        merged_df['best_bid_kelly'] = (merged_df['mean'] - (1 - merged_df['mean']) / (1/merged_df['best_bid']-1))
        merged_df['best_ask_kelly'] = (merged_df['mean'] - (1 - merged_df['mean']) / (1/merged_df['best_ask']-1))
        if not os.path.exists(f'database/{self.league}/signals'):
            os.makedirs(f'database/{self.league}/signals')
        merged_df.to_csv(f'database/{self.league}/signals/{self.league}_signal_{datetime.now().date()}_{datetime.now().hour}.csv', index_label=False)
        return merged_df


    def update_markets(self) -> None:

        for market in self.markets:
            market.update_market()

        self.last_update_markets = datetime.now()

        return None