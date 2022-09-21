import sqlite3
from flask import Flask, render_template, request, g, session, redirect
from pycoingecko import CoinGeckoAPI
import pandas as pd
import mplfinance as mpf
from PIL import Image
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash


from functions import draw_chart, check_coin, percentage, uppercase, usd, get_db, query_db, login_required, error

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


currency = "usd"
# Custom filters
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters["percentage"] = percentage
app.jinja_env.filters["upper"] = uppercase

@app.route('/')
@login_required
def index():

    username = session["user_id"][1]

    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"][0]
    cur.execute("SELECT * FROM portfolio WHERE user_id =?", (user_id,))
    data = cur.fetchall()
    portfolio = []
    global_value = 0
    global_cost = 0
    global_profit = 0
    
    for row in data:
        average_price = row[4] / row[3]
        coin_data = cg.get_coin_by_id(row[1])
        coin_price = round(coin_data["market_data"]["current_price"]["usd"], 2)
        current_value =  round(coin_price* row[3], 2)
        total_cost = round(row[4], 2)
        profit = round(current_value - total_cost, 2)
        portfolio.append({"name": row[1], "symbol": row[2],"amount":row[3],"average_price_paid": average_price,
                         "current_value": current_value, "total_cost": total_cost, "profit": profit, "coin_price": coin_price })
        global_value =+ current_value
        global_cost =+ total_cost
        global_profit =+ profit

    
    return render_template("index.html", username=username, portfolio=portfolio, global_value=global_value, 
                            global_cost=global_cost, global_profit=global_profit)


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

    #Show all the available coins in the Coingecko API
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

        #Verify the data was provided correctly
        if not coin_name:
            return error("Missing coin name")

        if not number_coins:
            return error("Missing number coins")

        if not transaction_size:
            return error("Missing total price")

        if not purchase_day:
            return error("Missing date of transaction")

        price_coin = transaction_size / number_coins
        try:
            result = check_coin(coin_name)
            if result == None:
                return redirect("/coinlist")        
        except:
            # If coin cannot be found it redirects the user to a page that shows all the coins that exist
            return redirect("/coinlist") 
        
        #Check that the coins sold do not exceed the coins available in portfolio
        check = query_db("SELECT * FROM portfolio WHERE coin_name = ? AND user_id = ?", (coin_name, session["user_id"][0]), one=True)
        if number_coins < 0:
            if check is None:
                return error("not enough balance")
            if abs(number_coins) > check[3]:
                return error("not enough balance")


        #Add data to history table
        info = cg.get_coin_by_id(coin_name)
        db = get_db()
        db.execute("INSERT INTO history (user_id, coin_name, symbol, number_coins, transaction_size, price_coin, currency, purchase_day) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (session["user_id"][0], info["id"], info["symbol"], number_coins, transaction_size, price_coin, currency, purchase_day))
        db.commit()

        #Add data to portfolio table        
        if check is not None:
        
            number_coins = number_coins + check[3]
            total_cost = transaction_size + check[4]
            db.execute("UPDATE portfolio SET coins = ? WHERE user_id = ? AND symbol = ?", (number_coins, session["user_id"][0], info["symbol"]))         
            db.execute("UPDATE portfolio SET total_cost = ? WHERE user_id = ? AND symbol = ?", (total_cost, session["user_id"][0], info["symbol"]))
            db.commit()
            return redirect("/transactions")
        else:
            #Check that the coins sold do not exceed the coins available in portfolio
            if number_coins < 0:
       
                    return error("not enough balance")

            db.execute("INSERT INTO portfolio (user_id, coin_name, symbol, coins, total_cost) VALUES (?, ?, ?, ?, ?)", (session["user_id"][0], info["id"], info["symbol"], number_coins,transaction_size))
            db.commit()
        return redirect("/transactions")

    else:
        #Displays a table with all transactions
        db = get_db()
        cur = db.cursor()
        user_id = session["user_id"][0]
        cur.execute("SELECT * FROM history WHERE user_id =?", (user_id,))
        transactions = cur.fetchall()

        return render_template("transactions.html", transactions=transactions)

@app.route('/tax', methods=["GET", "POST"])
@login_required
def tax():

    if request.method == "POST":

        rate = request.form.get("rate")
        allowance = request.form.get("allowance")
        start = request.form.get("tax_year_start")
        end = request.form.get("tax_year_end") 

        print(session["user_id"][0])
        transactions = query_db("SELECT * FROM history WHERE user_id = ?", [session["user_id"][0]], one=False)
        print(transactions)

        return render_template("tax.html")
    
    else:
        return render_template("tax.html")

@app.route('/register', methods=["GET", "POST"])
def register():


    if request.method == "POST":

        username = request.form.get("username")
        

        if not username:
            return error("Missing username")

        if not request.form.get("password"):
            return error("Missing password")

        if not request.form.get("confirmation"):
            return error("Missing confirmation")

        if request.form.get("confirmation") != request.form.get("password"):
            return error("Passwords don't match")
        
        hash = generate_password_hash(request.form.get("password"))

        check = query_db("SELECT * FROM users WHERE username = ?", [username], one=True)
        if check is not None:
            return error("user already exist")

        #Add user to the database
        db = get_db()
        db.execute("INSERT INTO users (username, hash, currency) VALUES (?, ?)", (username, hash, currency))
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
            return error("Invalid username and/or password")

        session["user_id"] = user[0]
       
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