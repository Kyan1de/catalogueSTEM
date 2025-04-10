# everything exclusively for the website
from flask import Flask, render_template, redirect, url_for, current_app, request
from markupsafe import escape

# for database stuff
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# moving flask's log ouput
from logging.config import dictConfig

# lets me have the input and server running at the same time
from multiprocessing import Process

# pretty tables for the command line tool
import tabulate

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

with app.app_context():
    db.create_all()

# attaches the function to the provided route
@app.route("/")
@app.route("/index")
def index():
    return render_template('index.html')

@app.route("/db/")
def lookup():
    data: list[Entry] = db.session.execute(db.select(Entry).order_by(Entry.name)).scalars().all()
    return render_template('dbTemplate.html', data=[[entry.name, entry.locationText, f"{entry.available} / {entry.booked}", "button goes here"] for entry in data])

#   handles command-line input. 
#   this will be the only way of adding things to the database for now 
# because adding logins and forms, and handling POST requests is a little out-of-scope
# (this will probably change at some point)
def CLIHandler(appProc: Process):
    with app.app_context():
        while True:
            userInput = input(" CATA > ").rstrip().lstrip()
            try: 
                if userInput.lower() == "quit":
                    print("shutting down...")
                    appProc.kill()
                    appProc.join()
                    appProc.close()
                    quit()
                elif userInput.lower().startswith("add"):
                    cmd = userInput.split(" ")
                    # either adding a new entry          [name locationtext locationimg numberavailable]
                    # or adding more of a specific entry [name number]
                    if len(cmd) == 5:
                        try:
                            db.session.add(Entry(name=cmd[1], locationText=cmd[2], locationImg=cmd[3], available=cmd[4], booked=0))
                        except Exception as e:
                            print(f"failed to add entry, it may already exist\n{e}")
                    elif len(cmd) == 3:
                        en:Entry = Entry.query.filter_by(name=cmd[1]).first()
                        if en is None:
                            print("Entry doesnt exist yet, try adding it with information on the location")
                        else:
                            if cmd[2].isdigit():
                                en.available += int(cmd[2])
                            elif "." in cmd[2]: # change image of the location
                                en.locationImg = cmd[2]
                            else:
                                en.locationText = cmd[2]
                    else:
                        print("invalid syntax")
                elif userInput.lower().startswith("view"):
                    # either:
                    #   view table
                    #   view table SQLQUERY
                    # table can only be 'entries' or 'bookings'
                    cmd = userInput.split(" ")
                    if len(cmd) == 2:
                        if cmd[1] == 'entries':
                            data:list[Entry] = db.session.execute(db.select(Entry).order_by(Entry.name)).scalars().all()
                            offset = 0
                            ENTRIES_PER_PAGE = 10
                            end=False
                            while not end:
                                print(
                                    tabulate.tabulate(
                                        [[element.id, element.name, element.locationText, element.locationImg, element.available, element.booked] for element in data[offset:min(offset+ENTRIES_PER_PAGE, len(data))]], 
                                        ("id", "name", "location text", "location image", "available", "booked"),
                                        maxcolwidths=10
                                    )
                                )
                                if len(data) < offset + ENTRIES_PER_PAGE:
                                    end = True
                                else:
                                    end = input(" CATA <e to end> ") == "e"
                        else:
                            print("invalid syntax")
                    else:
                        print("invalid syntax")
                elif userInput.lower() == "commit":
                    db.session.commit() # save whatever changes were made
                elif userInput.lower() == "help":
                    print("if this message is still here, bug Kya about it") # do this later
            except Exception as e:
                # unhelpful? yes. will I make it better? if I have time. 
                print(f"something went wrong, please check your command in the help menu\nrolling back changes to SQL\n{e}") 

def runFlask():
    #setup logging
    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }},
        'handlers': {'wsgi': {
            'class': 'flaskLogger.myStreamHandler',
            'formatter': 'default'
        }},
        'root': {
            'level': 'INFO',
            'handlers': ['wsgi']
        }
    })
    app.run()

if __name__ == "__main__":
    appProc = Process(target=runFlask)
    appProc.start()
    CLIHandler(appProc)