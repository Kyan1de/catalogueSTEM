# everything exclusively for the website
from flask import Flask, render_template, redirect, url_for, current_app, request
from markupsafe import escape

# for database stuff
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# for opening the flask log in a different console window thing
from multiprocessing import Process, Manager
import subprocess
import atexit

#initializing all the flask sqlalchemy stuff
class dBase(DeclarativeBase):
    pass
db = SQLAlchemy(model_class=dBase)
class Entry(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    locationText: Mapped[str] = mapped_column() # text description for the entry's location
    locationImg: Mapped[str] = mapped_column() # url for the image to display on hover
    available: Mapped[int] = mapped_column() # tracks available instances of the entry
    booked: Mapped[int] = mapped_column() # tracks booked instances of the entry

# handles the web application
app = Flask(__name__)
# connects the database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
# initialize the db with the app
db.init_app(app)

# init later, multi-window shenanigans
shared_dict = None

with app.app_context():
    db.create_all()

# attaches the function to the provided route
@app.route("/")
@app.route("/index")
def index():
    return render_template('index.html', msg=shared_dict["message"])

@app.route("/db/")
def lookup():
    data: list[Entry] = db.session.execute(db.select(Entry).order_by(Entry.name)).scalars().all()
    for e in data:
        print(e.__dict__)
    return render_template('dbTemplate.html', data=[[entry.name, entry.locationText, f"{entry.available} / {entry.booked}", "button goes here"] for entry in data])

#   handles command-line input. 
#   this will be the only way of adding things to the database for now 
# because adding logins and forms, and handling POST requests is a little out-of-scope
# (this will probably change at some point)
def CLIHandler(flask_window: subprocess.Popen):
    while True:
        userInput = input(" CATA > ")
        try: 
            if userInput.lower() == "quit":
                print("shutting down...")
                flask_window.kill()
                quit()
            elif userInput.lower().startswith("set"):
                _, key, val = userInput.split(" ")
                shared_dict[key] = val
            elif userInput.lower() == "help":
                pass # do this later
        except Exception as e:
            # unhelpful? yes. will I make it better? if I have time. 
            print("something went wrong, please check your command in the help menu or remove any extrenuous spaces") 

def run_flask(shared_dict):
    global shared_data
    shared_data = shared_dict  # Shared data between processes
    app.run()

if __name__ == "__main__":
    with Manager() as man:

        shared_dict = man.dict()
        shared_dict["message"] = "hi hello i hope this works"

        # start the flask server as a "separate" process
        flask_proc = subprocess.Popen(
                    ["start", "cmd", "/k", f"python -c \"from __main__ import run_flask; run_flask({shared_dict})\""],
                    shell=True
                )
        atexit.register(flask_proc.kill) # makes sure the site goes down when the main process closes
        # start the input loop
        CLIHandler(flask_proc)