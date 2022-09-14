import sqlite3
from flask import Flask, render_template, request, g, url_for, redirect
from pycoingecko import CoinGeckoAPI
import pandas as pd
from IPython import display
import mplfinance as mpf
from PIL import Image

from functions import draw_chart

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

cg = CoinGeckoAPI()

ids = cg.get_coins_list(include_platform = "false")

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

    if request.method == "POST":

        data = request.form.get("coin").lower()

        for r in ids:
            print(data)
            print(r["id"])
            if r["id"] == data:
                print("match")
                duration = request.form.get("duration")
                coin = request.form.get("coin").lower()
                draw_chart(coin,duration)
                return render_template("search.html", coin=coin, duration=duration)                
        else:
            return "Coin does not exist"
      
        
    else:
       
        img = Image.open("static/blank.png")
        img = img.save("static/chart.png")

        return render_template("search.html")






# No caching at all for API endpoints.
@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == '__main__':
    app.run(debug=True)