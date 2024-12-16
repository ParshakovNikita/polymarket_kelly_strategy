from py_clob_client.constants import POLYGON, AMOY
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
import json
import re


class Polymarket_connector:


    def __init__(self, path_to_args) -> None:

        self.name = 'Polymarket_connector'

        with open(path_to_args, 'r', encoding='utf-8') as json_file:
            private_kargs = json.load(json_file)

        self.host = private_kargs['host']
        self.key = private_kargs['key']
        self.chain_id = POLYGON

        self.client = ClobClient(host=self.host, key=self.key, chain_id=self.chain_id)
        self.client.set_api_creds(self.client.create_or_derive_api_creds())
        print('Succesfully auth with Poly')


class Market:

    def __init__(self, client: ClobClient, condition_id: str, league: str) -> None:
        self.name = 'Market'
        self.client = client
        self.condition_id = condition_id
        self.league = league
        self.update_market()

        try:
            self.team_name = self.extract_team_name()
        except Exception as e:
            self.team_name = ""
            print('Market.__init__', e, 'condition_id:', self.condition_id)

    def update_market(self) -> None:
        market_dict = self.client.get_market(condition_id=self.condition_id)

        self.question = market_dict['question']
        self.description = market_dict['description']
        self.minimum_order_size = market_dict['minimum_order_size']
        self.game_start_time = market_dict['game_start_time']
        self.status = 1
        if market_dict['closed'] == True:
            self.status = 0
            return None

        self.team_0_id = market_dict['tokens'][0]['token_id']
        self.team_1_id = market_dict['tokens'][1]['token_id']
        self.team_0_outcome = market_dict['tokens'][0]['outcome']
        self.team_1_outcome = market_dict['tokens'][1]['outcome']
        try:
            self.team_0_ob = self.client.get_order_book(token_id=self.team_0_id)
            self.team_1_ob = self.client.get_order_book(token_id=self.team_1_id)
            self.team_0_best_bid = self.team_0_ob.bids[-1] if float(self.team_0_ob.bids[-1].size) >= 100 else self.team_0_ob.bids[-2]
            self.team_0_best_ask = self.team_0_ob.asks[-1] if float(self.team_0_ob.asks[-1].size) >= 100 else self.team_0_ob.asks[-2]
            self.team_1_best_bid = self.team_1_ob.bids[-1] if float(self.team_1_ob.bids[-1].size) >= 100 else self.team_1_ob.bids[-2]
            self.team_1_best_ask = self.team_1_ob.asks[-1] if float(self.team_1_ob.asks[-1].size) >= 100 else self.team_1_ob.asks[-2]
        except Exception as e:
            print('Market.update_market()', e, 'question:', self.question)
            self.status = 0

        return None

        # print(market_dict)
        # self.match_time = market_dict['']
        # if self.league == 'EPL':
        #     for token in market_dict['tokens']:
        #         if token['outcome'] == 'Yes':
        #             self.yes_token_id = token['token_id']
        #             self.yes_token_price = token['price']
        #             self.yes_token_order_book = self.client.get_order_book(token_id=self.yes_token_id)
        #             self.yes_best_bid = self.yes_token_order_book.bids[-1] if float(self.yes_token_order_book.bids[-1].size) >= 100 else self.yes_token_order_book.bids[-2]
        #             self.yes_best_ask = self.yes_token_order_book.asks[-1] if float(self.yes_token_order_book.asks[-1].size) >= 100 else self.yes_token_order_book.asks[-2]
        #         elif token['outcome'] == 'No':
        #             self.no_token_id = token['token_id']
        #             self.no_token_price = token['price']
        #             self.no_token_order_book = self.client.get_order_book(token_id=self.no_token_id)
        #             self.no_best_bid = self.no_token_order_book.bids[-1] if float(self.no_token_order_book.asks[-1].size) >= 100 else self.no_token_order_book.asks[-2]
        #             self.no_best_ask = self.no_token_order_book.asks[-1] if float(self.no_token_order_book.asks[-1].size) >= 100 else self.no_token_order_book.asks[-2]
        #     del market_dict

    

    # def extract_team_name(self, question) -> str:
    #     words = question.split()
    #     if len(words) >= 3 and words[0] == "Will" and words[-4] == "win":
    #         return words[2]
    #     return None
    
    def extract_team_name(self):
        if self.league == "EPL":
            pattern = r'Will (.+?) win'
            if "draw" in self.question:
                pattern = r'Will (.+?) end'
        elif self.league == "NCAA":
            pattern = r'Will (.+?) win'
        else:
            pattern = r'Will the (.+?) win'
        match = re.search(pattern, self.question)
        
        if match:
            return match.group(1)
        return None

