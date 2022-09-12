import sqlite3
from flask import Flask, render_template, request, g

app = Flask(__name__)

@app.route('/')
def index():
    data = get_db()
    return str(data)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect("/home/aleix/cryptotax/cryptotax.db")
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


if __name__ == "_main__":
    app.run
    