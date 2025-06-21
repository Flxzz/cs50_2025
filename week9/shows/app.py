from flask import Flask, redirect, render_template, request, session, jsonify
from flask_session import Session
from cs50 import SQL

app = Flask(__name__)

db = SQL("sqlite:///shows.db")

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    q = request.args.get("q")
    if q:
        shows = db.execute("SELECT * FROM shows WHERE title LIKE ? LIMIT 20", "%" + request.args.get("q") + "%")
    else:
        shows = []
    return jsonify(shows)