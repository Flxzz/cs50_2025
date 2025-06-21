import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

def current_cash(id):
    return db.execute("SELECT cash FROM users WHERE id = ?", id)[0]["cash"]

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.execute("SELECT * FROM stocks WHERE user_id = ? ORDER BY symbol", session["user_id"])
    stock_total = 0
    for stock in stocks:
        stock["price"] = lookup(stock["symbol"])["price"]
        stock["total"] = stock["price"] * stock["shares"]
        stock_total += stock["total"]
        stock["price"] = usd(stock["price"])
        stock["total"] = usd(stock["total"])
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    cash = user[0]["cash"]
    total = stock_total + cash
    return render_template("index.html", stocks=stocks, cash=usd(cash), total=usd(total))



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    
    #POST
    symbol = request.form.get("symbol")
    shares = int(request.form.get("shares"))
    if shares <= 0:
        return apology("invalid shares")
    stock = lookup(symbol)
    if stock == None:
        return apology("invalid symbol")

    # get cash
    cash = current_cash(session["user_id"])
    price = stock["price"]
    if shares * price > cash:
        return apology("can't afford")
    
    # purchase
    userid = session["user_id"]
    symbol = stock["symbol"]
    # 记录这次购买
    db.execute("INSERT INTO purchases(user_id, symbol, shares, price) VALUES(?, ?, ?, ?)", userid, symbol, shares, price)
    # 更新现金
    cash = cash - shares * price
    db.execute("UPDATE users SET cash=? WHERE id = ?", cash, userid)
    # 更新账户
    stock = db.execute("SELECT * FROM stocks WHERE symbol = ? AND user_id = ?", symbol, userid)
    if len(stock) == 0:
        db.execute("INSERT INTO stocks(user_id, symbol, shares) VALUES(?, ?, ?)", userid, symbol, shares)
    else:
        shares += stock[0]["shares"]
        db.execute("UPDATE stocks SET shares = ? WHERE user_id = ? AND symbol = ?", shares, userid, symbol)
    flash("Bought!")
    return redirect("/")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    historys = db.execute("SELECT * FROM purchases WHERE user_id = ?", session["user_id"])
    return render_template("history.html", historys=historys)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")

    #"POST"
   
    symbol = request.form.get("symbol")
    stock = lookup(symbol)
    if stock:
        return render_template("quoted.html", stock = stock)
    return apology("invalid symbol")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        
        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide confirmation", 403)

        # Ensure password and confirmation match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 403)

        # Insert into db
        try:
            db.execute("INSERT INTO users(username, hash) VALUES (?, ?);", request.form.get("username"), generate_password_hash(request.form.get("password")))
        except ValueError:
            return apology("username already exists!", 403)
        
        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Remember this user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        flash("Registered!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    stocks = db.execute("SELECT * FROM stocks WHERE user_id = ? ORDER BY symbol", session["user_id"])

    if request.method == "GET":
        return render_template("sell.html", stocks = stocks)
    
    # POST
    symbol = request.form.get("symbol")
    shares = int(request.form.get("shares"))

    # d: {"symbol" : shares} 直接用d[symbol]获取目前有多少shares
    d = {}

    # 判断几种报错情况
    exist = False
    for stock in stocks:
        d[stock["symbol"]] = stock["shares"]
        if symbol == stock["symbol"]:
            exist = True
            break
    if not exist:
        return apology("invalid symbol")
    
    if shares <= 0 or shares > d[symbol]:
        return apology("invalid shares")
    
    # 目前的股价
    price = lookup(symbol)["price"]

    # 卖出的钱数
    got = price * shares

    # 剩余股票数
    remaining = d[symbol] - shares

    # 目前现金
    cash = current_cash(session["user_id"])

    # 更新现金
    cash = cash + got
    db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])

    # 更新股票
    if remaining == 0:
        db.execute("DELETE FROM stocks WHERE symbol = ? AND user_id = ?", symbol, session["user_id"])
    else:
        db.execute("UPDATE stocks SET shares = ? WHERE symbol = ? AND user_id = ?",remaining, symbol, session["user_id"])

    # 记录
    db.execute("INSERT INTO purchases(user_id, symbol, shares, price) VALUES(?,?,?,?)",session["user_id"], symbol, -shares, price)

    return redirect("/")