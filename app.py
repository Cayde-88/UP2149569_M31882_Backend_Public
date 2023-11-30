# import libraries

# for checking trading day
import datetime
import pandas_market_calendars as mcal

# for getting SP500 data
import bs4 as bs
import requests
import nasdaqdatalink as ndl
import datetime
import numpy as np
import warnings

# for performing SQL queries
import sqlalchemy as db
import pandas as pd

# for performing trades
import alpaca_trade_api as tradeapi
import yfinance as yf
import time

# ignore warnings
warnings.filterwarnings('ignore')

# import email_client
from email_client import send_email

def run_bot():

    from secret.secret import host, database, user, password

    today = datetime.date.today()
    us_cal = mcal.get_calendar('NYSE')
    schedule = us_cal.schedule(start_date=today, end_date=today)
    engine = db.create_engine(f'mysql+pymysql://{user}:{password}@{host}/{database}')

    # check if weekend (Saturday or Sunday)
    if today.weekday() >= 5 or len(schedule) == 0:
        print("It's the weekend or a holiday, no trading today")

        # drop rows with "Cancel" status - this is to prevent any repeat emails
        engine.execute("""DELETE FROM users WHERE days_to_trade = 'Cancel'""")
        pass

    # if not weekend or holiday, continue with trading algorithm
    else:
        today_schedule = schedule.iloc[0]

        if today_schedule["market_open"] is not None:

            # =============== Perform SQL queries =============== #
            # if table is empty, exit:
            if engine.execute("""SELECT * FROM users""").fetchall() == []:
                print("No users in database, trading algorithm exited.")
                pass

            else:
                # drop rows with "Cancel" status
                engine.execute("""DELETE FROM users WHERE days_to_trade = 'Cancel'""")

                # update remaining users' days_to_trade -= 1, leave those with "Indefinite" status unchanged
                engine.execute("""UPDATE users SET days_to_trade = days_to_trade - 1 WHERE days_to_trade <> 'Indefinite' """)

                # update those with days_to_trade = 0 to "Cancel" (will be deleted in next run)
                engine.execute("""UPDATE users SET days_to_trade = 'Cancel' WHERE days_to_trade = '0'""")

                # fetch all rows from users table
                result = engine.execute("""SELECT * FROM users""").fetchall()
                print("SQL related tasks completed.")

                # unpack result to dataframe
                users_table = pd.DataFrame(result, columns = ["api_key", "secret_key", "days_to_trade", "email", "date_submitted"])

                # =============== Get SP500 data ==================== #
                resp = requests.get('http://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
                soup = bs.BeautifulSoup(resp.text, 'lxml')
                table = soup.find('table', {'class': 'wikitable sortable'})
                tickers = []
                for row in table.findAll('tr')[1:]:
                    ticker = row.findAll('td')[0].text
                    tickers.append(ticker)

                tickers = [s.replace('\n', '') for s in tickers]

                # List of tickers to remove (update accordingly based on log)
                tickers_to_remove = ['LNT', 'BRK.B', 'BF.B']

                # Final list of tickers
                tickers = [ticker for ticker in tickers if ticker not in tickers_to_remove]

                start = datetime.datetime(2022, 1, 1)
                end = datetime.datetime.now()
                start_str = start.strftime('%Y-%m-%d')
                end_str = end.strftime('%Y-%m-%d')

                # initialize empty dataframe
                data = pd.DataFrame()

                # get the stock data, iteratively as PythonAnywhere doesn't allow multithreading
                for ticker in tickers:
                    ticker_data = yf.download(ticker, start = start_str, end = end_str, progress=False)["Close"].to_frame()
                    ticker_data.rename(columns = {"Close": ticker}, inplace=True)
                    data = pd.concat([data, ticker_data], axis=1)

                print("SP500 data retrieved.")

                # =============== Calculate Trading Signals =============== #
                calc_signal_data = data.copy()

                for symbol in data.columns:

                    # middle band
                    calc_signal_data[f"{symbol}_Middle_Band"] = data[symbol].rolling(window=20).mean()

                    # calculate standard deviation
                    calc_signal_data[f"{symbol}_Std"] = data[symbol].rolling(window=20).std()

                    # calculate upper and lower bands
                    num_std = 1.5
                    calc_signal_data[f"{symbol}_Upper_Band"] = calc_signal_data[f"{symbol}_Middle_Band"] + (calc_signal_data[f"{symbol}_Std"] * num_std)
                    calc_signal_data[f"{symbol}_Lower_Band"] = calc_signal_data[f"{symbol}_Middle_Band"] - (calc_signal_data[f"{symbol}_Std"] * num_std)

                    # generate buy and sell signals
                    buy_signal = np.where(data[symbol] < calc_signal_data[f"{symbol}_Lower_Band"], True, False)
                    calc_signal_data[f"{symbol}_Buy_Signal"] = buy_signal

                    sell_signal = np.where(data[symbol] > calc_signal_data[f"{symbol}_Upper_Band"], True, False)
                    calc_signal_data[f"{symbol}_Sell_Signal"] = sell_signal

                # reset index
                calc_signal_data.reset_index(inplace=True)

                # only keep buy and sell signals in the past 7 days
                calc_signal_data = calc_signal_data.iloc[-7:, :]

                # generate buy and sell signals
                buy_list = []
                sell_list = []
                for symbol in data.columns:
                    if calc_signal_data[f"{symbol}_Buy_Signal"].any() == True:
                        buy_list.append(symbol)

                    elif calc_signal_data[f"{symbol}_Sell_Signal"].any() == True:
                        sell_list.append(symbol)

                # remove duplicates in buy_list against sell_list
                buy_list = list(set(buy_list) - set(sell_list))
                print("Trading signals generated.")


                # =============== Send Trading Signals to Users =============== #
                for api_key, secret_key in zip(users_table["api_key"], users_table["secret_key"]):

                    try:
                        trading_client = tradeapi.REST(api_key, secret_key, base_url='https://paper-api.alpaca.markets', api_version='v2')
                        account = trading_client.get_account()
                        positions = trading_client.list_positions()

                        if account.trading_blocked == True:
                            print(f"Account {api_key} is blocked.")
                            pass

                        elif float(account.buying_power) > 0.00:

                            for symbol in buy_list:
                                # allocate by ticker price
                                ticker = yf.Ticker(symbol).info
                                market_price = ticker["currentPrice"]
                                qty = float(account.buying_power) // len(buy_list) // float(market_price)

                                try:
                                    # if the user already has a position in the stock, pass
                                    for position in positions:
                                        if symbol == position.symbol:
                                            pass
                                        else:
                                            trading_client.submit_order(symbol = symbol, qty = qty, side = 'buy', type = 'market', time_in_force = 'day')
                                            time.sleep(0.5)

                                # if insufficient buying power, pass
                                except tradeapi.rest.APIError as e:
                                    pass

                            # sell all positions in sell_list
                            for position in positions:
                                symbol = position.symbol
                                qty = position.qty

                                if symbol in sell_list:
                                    try:
                                        trading_client.submit_order(symbol = symbol, qty = qty, side = 'sell', type = 'market', time_in_force = 'day')

                                    # if order already submitted but not filled, pass
                                    except tradeapi.rest.APIError as e:
                                        pass

                        else:
                            # sell all positions in sell_list
                            for position in positions:
                                symbol = position.symbol
                                qty = position.qty

                                if symbol in sell_list:
                                    try:
                                        trading_client.submit_order(symbol = symbol, qty = qty, side = 'sell', type = 'market', time_in_force = 'day')

                                    # if order already submitted but not filled, pass
                                    except tradeapi.rest.APIError as e:
                                        pass

                    # if API key or secret key is invalid, drop from database
                    except requests.exceptions.HTTPError as e:

                        # if 403 error, drop from database
                        if e.response.status_code == 403:
                            print(f"API key {api_key} is invalid, dropping from database.")
                            engine.execute(f"""DELETE FROM users WHERE api_key = '{api_key}'""")
                        else:
                            pass

                print("Trading algorithm completed.")

        else:
            print("Today is a holiday (Observed).")

# Run the functions
run_bot()
send_email()
