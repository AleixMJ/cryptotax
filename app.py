from crypt import methods
import sqlite3
from flask import Flask, render_template, request, g, session, redirect
from pycoingecko import CoinGeckoAPI
import pandas as pd
from IPython import display
import mplfinance as mpf
from PIL import Image
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash


from functions import draw_chart, check_coin, percentage, uppercase, usd, get_db, query_db, login_required

app = Flask(__name__)
app.secret_key ="testin_sessions_672123"
#Session setup
SESSION_TYPE = 'filesystem'
app.config["SESSION_PERMANENT"] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config.from_object(__name__)
Session(app)

#API
cg = CoinGeckoAPI()

# Custom filters
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters["percentage"] = percentage
app.jinja_env.filters["upper"] = uppercase

@app.route('/')
@login_required
def index():

    username = session["user_id"][1]

    return render_template("index.html", username=username)


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/markets')
def markets():
    
    #Displays a table with Cryptocurrency market data
    coins = cg.get_coins_markets(vs_currency="usd",price_change_percentage="24h,30d,1y")
    coins_df = pd.DataFrame(coins).head(100).round(2)
    inverted = coins_df.transpose()

    return render_template("markets.html", inverted = inverted)

@app.route('/search', methods=["GET", "POST"])
def search():

    #Search Coingecko API for the data input, and displays a chart + data on the coin
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
            # If coin cannot be found it redirects the user to a page that shows all the coins that exist
            return redirect("/coinlist") 

    else:
        #If the site is vist by get it only displays the forms that need to be filled to search
        info = {"description":{"en": ""}, "symbol":"","links":{"homepage":[""]},"market_data":{"current_price":{"usd":None},
                "market_cap":{"usd":None},"price_change_percentage_24h":"","price_change_percentage_30d":"",
                "price_change_percentage_1y":"","ath":{"usd":None}}}
        img = Image.open("static/blank.png")
        img = img.save("static/chart.png")

        return render_template("search.html", info=info)



@app.route('/coinlist', methods=["GET"])
def coinlist():

    #Shaw all the available coins in the Coingecko API
    coins = cg.get_coins_list()
    return render_template("coinlist.html", coins=coins)

@app.route('/transactions', methods=["GET", "POST"])
@login_required
def transactions():
    
    if request.method == "POST":

        coin_name = request.form.get("coin_name").lower()
        number_coins = float(request.form.get("number_coins"))
        transaction_size = float(request.form.get("transaction_size"))
        purchase_day = request.form.get("purchase_day")
        currency = "usd"  

        if not coin_name:
            return ("Missing coin name", 400)

        if not number_coins:
            return ("Missing number coins", 400)

        if not transaction_size:
            return ("Missing total price", 400)

        if not purchase_day:
            return ("Missing date of transaction", 400)

        price_coin = transaction_size / number_coins
        try:
            result = check_coin(coin_name)
            if result == None:
                return redirect("/coinlist")        
        except:
            # If coin cannot be found it redirects the user to a page that shows all the coins that exist
            return redirect("/coinlist") 
        
        info = cg.get_coin_by_id(coin_name)
        print(session["user_id"][0])
        print(info["id"])
        print(info["symbol"])
        db = get_db()
        db.execute("INSERT INTO history (user_id, coin_name, symbol, number_coins, transaction_size, price_coin, currency, purchase_day) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (session["user_id"][0], info["id"], info["symbol"], number_coins, transaction_size, price_coin, currency, purchase_day))
        db.commit()
        return redirect("/transactions")

    else:
        #Displays a table with all transactions
        db = get_db()
        cur = db.cursor()
        print(session["user_id"][0])
        user_id = session["user_id"][0]
        print(cur)
        cur.execute("SELECT * FROM history WHERE user_id =?", (user_id,))
        transactions = cur.fetchall()
        print(transactions)

        return render_template("transactions.html", transactions=transactions)


@app.route('/register', methods=["GET", "POST"])
def register():


    if request.method == "POST":

        username = request.form.get("username")
        

        if not username:
            return ("Missing username", 400)

        if not request.form.get("password"):
            return ("Missing password", 400)

        if not request.form.get("confirmation"):
            return ("Missing confirmation", 400)

        if request.form.get("confirmation") != request.form.get("password"):
            return ("Passwords don't match", 400)
        
        hash = generate_password_hash(request.form.get("password"))

        check = query_db("SELECT * FROM users WHERE username = ?", [username], one=True)
        if check is not None:
            return ("user already exist", 400)

        #Add user to the database
        db = get_db()
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, hash))
        db.commit()
        return redirect("/")

    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    #Log user out
    session.clear()

    if request.method == "POST":
        
        user = query_db("SELECT * FROM users WHERE username = ?", [request.form.get("username")], one=False)

        if len(user) != 1 or not check_password_hash(user[0][2], request.form.get("password")):
            return "Invalid username and/or password "

        session["user_id"] = user[0]
        print(session["user_id"])

        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    #Log user out

    session.clear()

    return redirect("/")


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