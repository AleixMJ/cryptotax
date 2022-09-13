import sqlite3
from flask import Flask, render_template, request, g, url_for
from pycoingecko import CoinGeckoAPI
import pandas as pd
from IPython import display
import mplfinance as mpf

app = Flask(__name__)

cg = CoinGeckoAPI()



@app.route('/')
def index():

    user = query_db('select * from users where id = ?',[1], one=True)
    
    if user is None:
        print('No such user')
    else:
        username = user[1]

    return render_template("index.html", username=username)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect("cryptotax.db")
    return db

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/markets')
def markets():
    
      
    coins = cg.get_coins_markets(vs_currency="usd",price_change_percentage="24h,30d,1y")
    coins_df = pd.DataFrame(coins).head(100).round(2)
    inverted = coins_df.transpose()

    return render_template("markets.html", inverted = inverted)

@app.route('/search', methods=["GET", "POST"])
def search():

    duration = "2"
    coin = "ethereum"

    historical = cg.get_coin_ohlc_by_id(id="ethereum", vs_currency="usd", days=7)
    hist_df = pd.DataFrame(historical)
    hist_df.columns = ["Time", "Open", "High", "Low", "Close"]
    hist_df["Time"] = pd.to_datetime(hist_df["Time"]/1000, unit="s")
    hist_df.set_index("Time", inplace=True)
    mpf.plot(hist_df.tail(200), type="candle", style="charles", title="ethereum", mav=(20,50), savefig="static/chart.png")
    
    return render_template("search.html")

if __name__ == '__main__':
    app.run(debug=True)