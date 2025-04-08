from flask import Flask, render_template, redirect, url_for, current_app
from markupsafe import escape

# handles the web application
app = Flask(__name__)

# attaches the function to the provided route
@app.route("/")
@app.route("/index")
def index():
    return render_template('index.html')

@app.route("/db/")
def db():
    return render_template('dbTemplate.html', data=[[a, a+1, a+2, a+3] for a in range(100)])