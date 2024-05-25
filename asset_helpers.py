# Libraries used
from datetime import datetime
from twelvedata import TDClient
import pandas as pd
from urllib.request import urlopen
from dotenv import load_dotenv 
import os
import yfinance as yf
import requests

load_dotenv()
API_KEY = os.getenv('API_KEY')
td = TDClient(apikey=API_KEY)


def get_index_prices(name, ticker):
    '''
    Given an index name and the ticker of an ETF that tracks it, the function
    looks for the index data and returns it in a Dataframe format
    Parameters:
    - name: String
    - ticker: String
    Returns:
    - return_data: pandas Dataframe
    '''
    with open('helpermodules\indices\\' + name + '.csv', 'r') as file:
        return_data = pd.read_csv(file, sep=",", names=["Date", ticker], skiprows=1)

    # yahoo finance date format is "2024-04-01", whereas the index data we have has a "2024-04" format
    return_data["Date"] += "-01"

    return return_data


class Asset:
    '''
    The Asset class helps managing single assets.

    To initialize it you have to input the following attributes:
    - type: (String) the asset type (stock, ETF, index, commodity, crypto, currency...)
    - ticker: (String) the ticker of the asset 
    - full_name: (String) full name of the asset

    NOTE: Use Asset.load() function to initialize the following attributes
    The following attributes are computed automatically using the assets list:
    - df: pandas dataframe of the asset (monthly)
    - isin: (String) ETF isin (if ETF, else None)
    - index_name: (String) ETF underlying index (if ETF, else None)
    - ter: (float) ETF ter (if ETF, else None)
    '''
    def __init__(self, type, ticker, full_name):
        self.type = type
        self.ticker = ticker
        self.full_name = full_name
        self.df = None
        self.isin = None
        self.index_name = None
        self.ter = None

    def apply_ter(self, ter):
        monthly_ter_pct = (ter/12)/100

        columns = self.df[self.ticker]
        
        new_df = columns.apply(lambda x: x - monthly_ter_pct)

        self.df[self.ticker] = new_df

    def load_etf_isin(self):
        with open('./very_long_html.txt', 'r') as file:
            data = file.read()

        # NOTA: spesso non trova l'etf a causa di parentesi o altre piccole differenze con justEtf, creare una funzione di ricerca
        #       con gerarchica basata su parole chiave (World, S&P 500, ...) piuttosto che cercare con .find()
        index = data.find(self.full_name.upper(),0)

        # se non trova nulla ritorna None
        if index == -1:
            return None

        i=0
        isin=""
        # getting the etf isin by reading from the fourth " symbol up to the fifth " symbol it encounters on the very_long_html file
        while (i<5):
            index+=1
            letter=data[index]
            if letter == '"':
                i+=1
            if (i>=4) & (letter!='"'):
                isin+=letter

        self.isin = isin
    
    def load_index_name(self):
        url = "https://www.justetf.com/en/etf-profile.html?isin=" + self.isin
        req = requests.get(url).text
        index_name = req.split("seeks to track the")[1].split(" index")[0]
        
        self.index_name = index_name

    def load_ter(self):
        if self.isin == None:
            return 

        with open('./very_long_html.txt', 'r') as file:
            data = file.read() # replace'\n', ''

        index = data.find(self.isin,0)

        i=0
        ter=""
        while (i<5):
            index+=1
            letter=data[index]
            if letter == '"':
                i+=1
            if (i>=4) & (letter!='"') & (letter!='%'):
                ter+=letter

        self.ter = ter
    
    def load_df(self):
        '''
        The load_df function downloads monthly open prices for self.ticker, calculates monthly percentage returns, retrieves
        and processes index prices and fills Nan values with the index data.

        Parameters:
            self: Instance of the class
        Output:
            Sets self.df to a DataFrame of monthly returns for the specified ticker
        ''' 

        ticker = self.ticker
        index_name = self.index_name

        portfolio_prices = yf.download([ticker, 'IBM'], interval='1mo')['Open']
        portfolio_prices = portfolio_prices.pct_change()

        return_data = get_index_prices(index_name, ticker)
        return_data[ticker] = return_data[ticker].pct_change()

        for i in range(0,len(return_data)):
            return_data.loc[i,"Date"] = datetime.strptime(return_data.loc[i,"Date"], '%Y-%m-%d')

        return_data.set_index("Date", inplace = True)
        portfolio_prices[ticker].fillna(return_data[ticker], inplace = True)
        
        portfolio_prices.drop("IBM", axis=1, inplace = True)
        portfolio_prices.dropna(axis = 0, how = 'all', inplace = True)

        self.df = portfolio_prices

    def load(self):
        if self.type == 'ETF':
            self.load_etf_isin()
            self.load_index_name()
            self.load_ter()
        self.load_df()
    
    def info(self):
        print("Full name: ", self.full_name)
        print("Ticker: ", self.ticker)
        print("Type: ", self.type)
        print("Ter: ", self.ter, "%")
        print("Index name: ", self.index_name)
        print("Isin: ", self.isin)
        print("Dataframe: \n", self.df)
    
    def get_etf_ticker(self):
        # FIXME: not working

        url = "https://www.justetf.com/it/etf-profile.html?isin=" + self.isin 

        print("URL HERE:")
        print(url)
        req = requests.get(url).text

        print(req)

        ticker = req.split('<span class="d-inline-block" id="etf-second-id">')[0].split('</span>')[0]
            
        return ticker

