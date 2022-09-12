import sqlite3
from flask import Flask, render_template, request, g
from pycoingecko import CoinGeckoAPI


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
    coins = []
    print(data["bitcoin"]["usd"])
    for coin in data:
                
        coins.append({"name": coin, "usd": data[coin]["usd"]})
    
    print(coins)
    return render_template("markets.html", data=data)