import sqlite3
import os
from flask import Flask, render_template, request, g, session, redirect
from pycoingecko import CoinGeckoAPI
import pandas as pd
import mplfinance as mpf
from PIL import Image
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import mysql.connector
from flask_sqlalchemy import SQLAlchemy
from functions import draw_chart, check_coin, percentage, uppercase, usd, get_db, query_db, login_required, error,configure
from dotenv import load_dotenv


configure()

app = Flask(__name__)
app.secret_key = os.getenv("SECRETKEY")

#Add Database
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")


db = SQLAlchemy(app)

class users(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    hash = db.Column(db.String(200))
    currency = db.Column(db.String(20))
    transactions = db.relationship("history", backref="transaction")
    portfolio = db.relationship("portfolio", backref="portfolio")

    def __init__(self, username, hash, currency):
        self.username = username
        self.hash = hash
        self.currency = currency


class history(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(50), nullable=False)
    number_coins = db.Column(db.Integer, nullable=False)
    transaction_size = db.Column(db.Integer, nullable=False)
    price_coin = db.Column(db.Integer, nullable=False)
    coin_name = db.Column(db.String(100), nullable=False)
    currency = db.Column(db.String(30), nullable=False)
    purchase_day = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    def __init__(self, symbol, number_coins, transaction_size, price_coin, coin_name, currency, purchase_day, user_id):
        self.symbol = symbol
        self.number_coins = number_coins
        self.transaction_size = transaction_size
        self.price_coin = price_coin
        self.coin_name = coin_name
        self.currency = currency
        self.purchase_day = purchase_day
        self.user_id = user_id

class portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coin_name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(50), nullable=False)
    coins = db.Column(db.Integer, nullable=False)
    total_cost = db.Column(db.Integer, nullable=False)  
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    def __init__(self, coin_name, symbol, coins, total_cost, user_id):
        self.coin_name = coin_name
        self.symbol = symbol
        self.coins = coins
        self.total_cost = total_cost
        self.user_id = user_id


db.create_all()

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

    username = session["user_id"]["username"]

    user_id = session["user_id"]["id"]
    data = portfolio.query.filter_by(user_id = user_id).all()
    portfolio2 = []
    global_value = 0
    global_cost = 0
    global_profit = 0
    
    for row in data:
        average_price = row.total_cost / row.coins
        coin_data = cg.get_coin_by_id(row.coin_name)
        coin_price = round(coin_data["market_data"]["current_price"]["usd"], 2)
        current_value =  round(coin_price* row.coins, 2)
        total_cost = round(row.total_cost, 2)
        profit = round(current_value - total_cost, 2)
        portfolio2.append({"name": row.coin_name, "symbol": row.symbol,"amount":row.coins,"average_price_paid": average_price,
                         "current_value": current_value, "total_cost": total_cost, "profit": profit, "coin_price": coin_price })
        global_value =+ current_value
        global_cost =+ total_cost
        global_profit =+ profit

    
    return render_template("index.html", username=username, portfolio2=portfolio2, global_value=global_value, 
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

        return render_template("search.html")



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
        number_coins = int(request.form.get("number_coins"))
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

        price_coin = transaction_size / abs(number_coins)
        try:
            result = check_coin(coin_name)
            if result == None:
                return redirect("/coinlist")        
        except:
            # If coin cannot be found it redirects the user to a page that shows all the coins that exist
            return redirect("/coinlist") 
        
        #Check that the coins sold do not exceed the coins available in portfolio
        check = portfolio.query.filter_by(coin_name=coin_name, user_id = session["user_id"]["id"]).first()
        if number_coins < 0:
            if check is None:
                return error("not enough balance")
            if abs(number_coins) > check.coins:
                return error("not enough balance")


        #Add data to history table
        info = cg.get_coin_by_id(coin_name)
        transaction = history(coin_name=info["id"], symbol=info["symbol"], number_coins=number_coins, transaction_size=transaction_size, price_coin=price_coin, currency=currency, purchase_day=purchase_day, user_id=session["user_id"]["id"])
        db.session.add(transaction)
        db.session.commit()

        #Add data to portfolio table        
        if check is not None:
            if number_coins < 0:
                total_cost = check.total_cost + (check.total_cost * (number_coins / check.coins))
            else:
                total_cost = check.total_cost + transaction_size

            number_coins = number_coins + check.coins
            portfolio_coin = portfolio.query.filter_by(user_id=session["user_id"]["id"], coin_name=coin_name).first()
            portfolio_coin.coins = number_coins
            portfolio_coin.total_cost = total_cost
            db.session.commit()
            return redirect("/transactions")
        else:
            #Check that the coins sold do not exceed the coins available in portfolio
            if number_coins < 0:
                           return error("not enough balance")

            transaction = portfolio(coin_name=info["id"], symbol=info["symbol"], coins=number_coins, total_cost=transaction_size, user_id=session["user_id"]["id"])
            db.session.add(transaction)
            db.session.commit()

        return redirect("/transactions")

    else:
        #Displays a table with all transactions

        user_id = session["user_id"]["id"]
        transactions = history.query.filter_by(user_id=user_id).all()

        return render_template("transactions.html", transactions=transactions)

@app.route('/tax', methods=["GET", "POST"])
@login_required
def tax():

    if request.method == "POST":

        rate = int(request.form.get("rate"))
        allowance = int(request.form.get("allowances"))
        start = datetime.strptime(request.form.get("tax_year_start"),  "%Y-%m-%d").date()      
        end = datetime.strptime(request.form.get("tax_year_end"),  "%Y-%m-%d").date()

        if start > end:
            return error("Tax year start date cannot happen after the tax year end date")
        
        user_taxes = history.query.filter_by(user_id = session["user_id"]["id"]).all()

        transactions = []
        tax = []
        total_profit = 0
 
        for row in user_taxes:
            print(row.purchase_day)
            print(type(row.purchase_day))
            date = datetime.strptime(row.purchase_day,  "%Y-%m-%d").date()
            print(type(date))
            transactions.append({"name": row.coin_name, "amount":row.number_coins,"date": date, "proceeds": row.transaction_size})

        # Calculate allowable cost based on the defined dates transactions
        for row in transactions:
             if row["date"] > start and row["date"] < end:
                total_cost = transactions[0]["proceeds"]
                total_coins = transactions[0]["amount"]
                for tx in transactions:
                    print(total_coins)
                    if tx["date"] < row["date"]:
                        total_coins += tx["amount"]
                        if tx["amount"] > 0:
                            total_cost += tx["proceeds"]

                average_price = round(total_cost / total_coins, 2)
                allowable_cost = round(average_price * abs(row["amount"]), 2)
                profit = round(row["proceeds"] - allowable_cost, 2)
                tax.append({"name": row["name"], "amount":row["amount"],"date": row["date"], 
                            "allowable_cost": allowable_cost, "proceeds": row["proceeds"], "profit": profit})
                total_profit += profit

        
        taxes_to_pay = round((total_profit * (rate / 100)) - allowance, 2)
        if taxes_to_pay < 0:
            taxes_to_pay = 0
        return render_template("tax.html", tax=tax, end=end, start=start, total_profit=total_profit, 
                                taxes_to_pay=taxes_to_pay)
    
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

        check = users.query.filter_by(username=username).first()
        if check is not None:
            return error("user already exist")

        #Add user to the database

        db.session.add(users(username, hash, currency))
        db.session.commit()

        return redirect("/")

    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    #Log user out
    session.clear()

    if request.method == "POST":
                
        user = users.query.filter_by(username=request.form.get("username")).first()

        if user == None or not check_password_hash(user.hash, request.form.get("password")):
            return error("Invalid username and/or password")

        session["user_id"] = {"id": user.id, "username": user.username,"hash":user.hash, "currency":user.currency}      
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