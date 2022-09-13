import sqlite3
from flask import Flask, render_template, request, g
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
    
    data = cg.get_price(ids = "bitcoin, ethereum", vs_currencies = "usd")
    
    coins = cg.get_coins_markets(vs_currency="usd",price_change_percentage="24h,30d,1y")
    coins_df = pd.DataFrame(coins).head(10)
    coins_df.set_index("id", inplace=True)
    print(coins_df.loc["bitcoin"]["current_price"])
    return render_template("markets.html", coins_df = coins_df)