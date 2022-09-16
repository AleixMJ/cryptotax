import sqlite3
from flask import Flask, render_template, request, g, url_for, redirect
from pycoingecko import CoinGeckoAPI
import pandas as pd
from IPython import display
import mplfinance as mpf
from PIL import Image

from functions import draw_chart, check_coin, percentage, uppercase, usd

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

#API
cg = CoinGeckoAPI()

# Custom filter
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters["percentage"] = percentage
app.jinja_env.filters["upper"] = uppercase


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

        try:
            result = check_coin(data)

            if result == None:
                return redirect("/coinlist")
            else:
                info = cg.get_coin_by_id(request.form.get("coin").lower())
                # Creates chart based on the duration and coin selected
                duration = request.form.get("duration")
                coin = request.form.get("coin").lower()
                draw_chart(coin,duration)
                return render_template("search.html", coin=coin, duration=duration, info=info)                
        except:
            return redirect("/coinlist") 

    else:
        info = {"description":{"en": ""}, "symbol":"","links":{"homepage":[""]},"market_data":{"current_price":{"usd":None},
                "market_cap":{"usd":None},"price_change_percentage_24h":"","price_change_percentage_30d":"",
                "price_change_percentage_1y":"","ath":{"usd":None}}}
        img = Image.open("static/blank.png")
        img = img.save("static/chart.png")

        return render_template("search.html", info=info)



@app.route('/coinlist', methods=["GET"])
def coinlist():

    coins = cg.get_coins_list()
    return render_template("coinlist.html", coins=coins)






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