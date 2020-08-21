import re
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def login_required(f):
    """
    Decorate routes to require login.
    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/about")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = "pk_31845308fe584a09a76591c8612ea1d3"
        response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


# Source: Stackoverflow (user: ePi272314)
# URL: https://stackoverflow.com/questions/16709638/checking-the-strength-of-a-password-how-to-check-conditions
# Date of retrieval: 8/11/20
def validate(password):
    # Validate password with these conditions:
    # 1. Minimum 8 characters
    # 2. The alphabets must be between [a-z]
    # 3. At least one alphabet should be of Upper Case [A-Z]
    # 4. At least 1 number or digit between [0-9]
    # 5. At least 1 character from [ _ or @ or $ ]

    # Condition 1: calculating the length
    length_error = len(password) < 8

    # Condition 2: searching for lowercase
    lowercase_error = re.search(r"[a-z]", password) is None

    # Condition 3: searching for uppercase
    uppercase_error = re.search(r"[A-Z]", password) is None

    # Condition 4: searching for digits
    digit_error = re.search(r"\d", password) is None
    
    # Condition 5: searching for symbols
    symbol_error = re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None

    # overall result
    password_ok = not ( length_error or digit_error or uppercase_error or lowercase_error or symbol_error )

    return {
        'password_ok' : password_ok,
        'length_error' : length_error,
        'digit_error' : digit_error,
        'uppercase_error' : uppercase_error,
        'lowercase_error' : lowercase_error,
        'symbol_error' : symbol_error,
    }
