from datetime import datetime

from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, lookup, validate

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

ENV = 'dev'

if ENV == 'dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:[password]@localhost/tradingwheels'
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = ''

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    hash = db.Column(db.Text, nullable=False)
    cash = db.Column(db.Float, default=10000.00)
    

    def __init__(self, username, hash):
        self.username = username
        self.hash = hash


class History(db.Model):
    __tablename__ = 'history'
    order_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    symbol = db.Column(db.String(5), nullable=False)
    shares = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    time = db.Column(db.DateTime, nullable=False)

    def __init__(self, user_id, symbol, shares, price, time):
        self.user_id = user_id
        self.symbol = symbol
        self.shares = shares
        self.price = price
        self.time = time


@app.route("/")
@login_required
def home():
    """Show portfolio of stocks"""

    user_id = session["user_id"]

    # Query database for user's portfolio information
    stocks = History.query.filter_by(user_id=user_id).all()
    
    # Select user's username and cash balance
    user = User.query.filter_by(id=user_id).first()
    username = user.username
    cash = user.cash

    portfolio = []
    total = 0
    
    for stock in stocks:
        flag = 0

        # Ignore MONEY since it represents money added to the account, not a stock
        if stock.symbol == "MONEY":
            continue

        # Loop through the portfolio list and update values if it's already in the list
        for i in range(len(portfolio)):
            if stock.symbol in portfolio[i]['symbol']:
                portfolio[i]['shares'] = round(portfolio[i]['shares'] + stock.shares, 2)
                val = stock.shares * portfolio[i]['price']
                portfolio[i]['total'] = round(portfolio[i]['total'] + val, 2)
                total += val
                # flag indicates that processing has already been done and loop should continue
                flag = 1
                break
        
        if flag == 1:
            continue

        # Lookup stock information
        info = lookup(stock.symbol)

        # Append each dictionary of stock information to the portfolio list
        portfolio.append({'symbol': stock.symbol, 'name': info["name"], 'shares': round(stock.shares, 2), 
                        'price': round(info["price"], 2), 'total': round(stock.shares * info["price"], 2)})
        
        # Aggregate value from stocks
        total += round(stock.shares * info["price"], 2)
    
    # Add buying power to total value
    total += cash
    total = round(total, 2)

    return render_template("index.html", portfolio=portfolio, cash=round(cash, 2), total=total, username=username)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Display registration page
    if request.method == "GET":
        return render_template("register.html")
    
    # Registration form was submitted
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return render_template("error.html", message="must provide username")

        # Ensure password was submitted
        elif not password:
            return render_template("error.html", message="must provide password")

        # Ensure confirmation was submitted
        elif not confirmation:
            return render_template("error.html", message="must provide confirmation")

        # Ensure password and confirmation match
        elif password != confirmation:
            return render_template("error.html", message="password and confirmation must match")
        
        # Check for duplicate username
        users = User.query.all()
        
        for usernames in users:
            if username == usernames.username:
                return render_template("error.html", message="username already exists")
        
        # Validate password
        validation = validate(password)

        if not validation["password_ok"]:
            error = list(validation.keys())[list(validation.values()).index(True)]
            return render_template("error.html", message=error)

        # Create hashed password
        hashed = generate_password_hash(password)

        # Store user info into database
        user = User(username, hashed)
        db.session.add(user)
        db.session.commit()

        return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Display login page
    if request.method == "GET":
        return render_template("login.html")
    
    # Login form was submitted
    else:
        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            return render_template("error.html", message="must provide username")

        # Ensure password was submitted
        elif not password:
            return render_template("error.html", message="must provide password")

        # Query database for username
        user = User.query.filter_by(username=username).all()

        # Ensure username exists and password is correct
        if len(user) != 1 or not check_password_hash(user[0].hash, password):
            return render_template("error.html", message="invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = user[0].id

        # Redirect user to home page
        return redirect("/")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add cash to account"""

    # Display add page
    if request.method == "GET":
        return render_template("add.html")

    # User submitted form to add cash
    else:
        user_id = session["user_id"]
        amount = request.form.get("amount")
        symbol = "MONEY"

        # Ensure amount was submitted
        if not amount:
            return render_template("error.html", message="must provide amount to be added")
        
        # Log in history
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log = History(user_id, symbol, 1, amount, time)
        db.session.add(log)
        db.session.commit()

        # Calculate user's final cash balance
        user = User.query.filter_by(id=user_id).first()
        curr_bal = user.cash
        fin_bal = round(int(amount) + curr_bal, 2)

        # Update user's cash balance
        user.cash = fin_bal
        db.session.commit()

        return redirect("/")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Execute purchase of stock shares"""

    # Display purchase page
    if request.method == "GET":
        return render_template("buy.html")

    # Purchase form was submitted
    else:
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")

        # Ensure symbol was submitted
        if not symbol:
            return render_template("error.html", message="must provide symbol")

        # Ensure symbol exists
        elif not lookup(symbol):
            return render_template("error.html", message="symbol does not exist")

        # Ensure shares was submitted
        elif not shares:
            return render_template("error.html", message="must provide number of shares")

        # Ensure shares is appropriate
        elif float(shares) <= 0:
            return render_template("error.html", message="# of shares is not appropriate")

        # Lookup stock price
        price = round(lookup(symbol)["price"], 2)

        # Lookup user balance
        user_id = session["user_id"]

        balance = User.query.filter_by(id=user_id).all()[0].cash

        # Check if request can be fulfilled
        if balance < price * float(shares):
            return render_template("error.html", message="sorry, balance is too low")
        
        # Execute purchase
        else:
            time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Log in history
        log = History(user_id, symbol, shares, price, time)
        db.session.add(log)
        db.session.commit()

        # Update user's cash balance
        balance -= price * float(shares)

        user = User.query.filter_by(id=user_id).first()
        user.cash = round(balance, 2)
        db.session.commit()

        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    user_id = session["user_id"]

    history = History.query.filter_by(user_id=user_id).distinct(History.symbol).all()
    stocks = []

    for row in history:
        if row.symbol == "MONEY":
            continue
        else:
            stocks.append(row)
    
    # Display sell page
    if request.method == "GET":
        return render_template("sell.html", stocks=stocks)
    
    # User submitted form to sell shares
    else:
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
    
        # Fetch number of shares that user owns for specified stock
        logs = History.query.filter_by(user_id=user_id, symbol=symbol).all()
        owned = 0

        for log in logs:
            owned += log.shares
        
        owned = round(owned, 2)

        # Ensure a stock was chosen
        if not symbol:
            return render_template("error.html", message="must select a stock")

        # Ensure shares was submitted
        elif not shares:
            return render_template("error.html", message="must provide number of shares")

        # Ensure shares is valid
        elif float(shares) <= 0 or float(shares) > owned:
            return render_template("error.html", message="invalid shares amount")

        # Sanity check to confirm that stock exists in portfolio 
        for i in range(len(stocks)):
            if symbol == stocks[i].symbol:
                break
            elif i == len(stocks) - 1:
                return render_template("error.html", message="stock not in portfolio")
        
        # Execute sell by logging in history
        price = round(lookup(symbol)["price"], 2)
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        log = History(user_id, symbol, -1*float(shares), price, time)
        db.session.add(log)
        db.session.commit()

        # Update user's cash balance
        user = User.query.filter_by(id=user_id).first()
        user.cash += price * float(shares)
        user.cash = round(user.cash, 2)
        db.session.commit()

        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]

    history = History.query.filter_by(user_id=user_id).order_by(History.time.desc()).all()

    return render_template("history.html", history=history)


@app.route("/quote", methods=["POST"])
def quote():
    """Get stock quote."""

    # User requests a quote for inputted stock
    if request.method == "POST":
        symbol = request.form.get("symbol")

        # Ensure symbol was submitted
        if not symbol:
            return render_template("error.html", message="must provide symbol")

        # Request stock info
        result = lookup(symbol)

        # Ensure symbol is valid
        if not result:
            return render_template("error.html", message="invalid symbol")

        return render_template("quote.html", name=result["name"], symbol=result["symbol"], price=round(result["price"], 2))


if __name__ == '__main__':
    app.run()
