from multiprocessing import connection
import sqlite3
from flask import Flask, render_template, request
app = Flask(__name__)


@app.route('/')
def index():


    return render_template("index.html")


@app.route('/test', methods = ["GET"])
def test():
    try:
        if request.method == "GET":
           connection = sqlite3.connect("crypto.db")
           db = connection.cursor() 
           result = db.execute("SELECT * FROM users WHERE id = ?", 1)
           result = result.fetchall()[0][0]
           return render_template("test.html", result = result)
    except:
        return render_template("test.html", result = "")

    