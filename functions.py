from lib2to3.pgen2.token import AT
from functools import wraps
from flask import Flask, render_template, request, g, session, url_for, redirect
from pycoingecko import CoinGeckoAPI
import pandas as pd
import mplfinance as mpf
from dotenv import load_dotenv

cg = CoinGeckoAPI()


def configure():
    load_dotenv()


def draw_chart(coin,duration):

        # Draws and saves as chart.png in the static folder a chart of the selected coin and the specific duration. 
        # It uses Coingecko APIs and available durations are (in days): 1, 7, 14, 30, 90, 180, 365 and "max"
        historical = cg.get_coin_ohlc_by_id(id=coin, vs_currency="usd", days=duration)
        hist_df = pd.DataFrame(historical)
        hist_df.columns = ["Time", "Open", "High", "Low", "Close"]
        hist_df["Time"] = pd.to_datetime(hist_df["Time"]/1000, unit="s")
        hist_df.set_index("Time", inplace=True)
        mpf.plot(hist_df.tail(200), type="candle", style="charles", title= coin.capitalize() + " Price Chart", mav=(20,50), savefig="static/chart.png")

def check_coin(coin):

    # Checks the coin against Coingecko database and returns all data or error if it doesn't exist.
    try:    
        response = cg.get_coin_by_id(coin)
        return response
    except:
        return None

def usd(value):
    #Format value as USD.
    if value == None:
        return ""
    return f"${value:,.2f}"

def percentage(value):
    #Format value as %
    if value == "":
        return ""
    else:
        return f"{value}%"

def uppercase(value):
    #Formats to uppercase
    if value == "":
        return ""
    else:
        return f"{value.upper()}"


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def error(message):

    return render_template("error.html", message=message)
