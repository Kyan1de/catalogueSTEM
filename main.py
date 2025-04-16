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
from time import sleep
import atexit

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

class Booking(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    bookedMaterial: Mapped[str] = mapped_column(unique=True)
    bookedBy: Mapped[str] = mapped_column()
    bookInfo: Mapped[str] = mapped_column()

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
    return render_template('dbTemplate.html', data=[[entry.name, entry.locationText, entry.locationImg, f"{entry.available} / {entry.booked}"] for entry in data])

@app.route("/book/<name>")
def booking(name):
    return render_template("index.html")

# handles command-line input. 
# this will be the only way of adding things to the database for now
def CLIHandler(appProc: Process):
    with app.app_context():
        while True:
            userInput = input(" CATA > ").rstrip().lstrip()
            try: 
                if userInput.lower() == "quit":
                    print("shutting down...")
                    print("(you may need to manually close the logging window)")
                    appProc.kill()
                    appProc.join()
                    appProc.close()
                    quit()
                elif userInput.lower().startswith("add"):
                    cmd = userInput.split(" ")
                    # add a new entry [name], asks for more info after
                    CLIAdd(cmd[1:])
                elif userInput.lower().startswith("edit"):
                    cmd = userInput.split(" ")
                    # edits the [locationText]
                    #           [locationImg]
                    #           [count]
                    CLIEdit(cmd[1:])
                elif userInput.lower().startswith("remove"):
                    cmd = userInput.split(" ")
                    # removes an entry [name]
                    # change later to allow for removing bookings?
                    CLIRemove(cmd[1:])
                elif userInput.lower().startswith("view"):
                    # either:
                    #   view table
                    # table can only be 'entries' or 'bookings'
                    cmd = userInput.split(" ")
                    CLIView(cmd[1:])
                elif userInput.lower() == "commit":
                    db.session.commit() # save whatever changes were made
                elif userInput.lower() == "help":
                    print("if this message is still here, bug Kya about it\n") # do this later
            except Exception as e:
                # unhelpful? yes. will I make it better? if I have time. 
                print(f"something went wrong, please check your command in the help menu\nrolling back changes to SQL\n{e}\n") 

def CLIAdd(command):
    try:
        if len(command) != 1: raise Exception("invalid syntax")
        locationText = input(f"describe the location of the '{command[0]}': ")
        locationImg = input("enter the file name of the image showing its location: ")
        available = int(input(f"how many '{command[0]}'s are there: "))
        db.session.add(Entry(name=command[0], locationText=locationText, locationImg=locationImg, available=available, booked=0))
    except Exception as e:
        print(f"failed to add entry, it may already exist\n{e}\n")

def CLIEdit(command):
    try:
        if len(command) != 2: raise Exception("invalid syntax")
        if command[1] not in ["locationText","locationImg","count"]: raise Exception("invalid attribute") 
        try:
            elements = db.session.execute(db.select(Entry).where(Entry.name.contains(command[0]))).scalars()
            print(
                tabulate.tabulate(
                    [[element.id, element.name, element.locationText, element.locationImg, element.available, element.booked] for element in elements], 
                    ("id", "name", "location text", "location image", "available", "booked"),
                    maxcolwidths=10
                ), "\n"
            )
        except Exception as e:
            print("no entries found\n")
        
        toEdit = ""
        while not toEdit.isdigit() and toEdit != "x":
            toEdit = input("enter the ID of the entry to edit (x to cancel): ")
        if toEdit == 'x':
            return
        else:
            element = db.session.execute(db.select(Entry).where(Entry.id == int(toEdit))).scalar_one()
            if command[1] == "count": element.available = int(input(f"new number of available {element.name}s: "))
            if command[1] == "locationText": input(f"text location of {element.name}: ")
            if command[1] == "locationImg": input(f"image location of {element.name}: ")
    except Exception as e:
        print(f"failed to edit entry, please check syntax\n{e}\n")

def CLIRemove(command):
    if len(command) == 1:
        try:
            elements = db.session.execute(db.select(Entry).where(Entry.name.contains(command[0]))).scalars()
            print(
                tabulate.tabulate(
                    [[element.id, element.name, element.locationText, element.locationImg, element.available, element.booked] for element in elements], 
                    ("id", "name", "location text", "location image", "available", "booked"),
                    maxcolwidths=10
                ), "\n"
            )
            toDelete = ""
            while not toDelete.isdigit() and toDelete != "x":
                toDelete = input("enter the ID of the entry to delete (x to cancel): ")
            if toDelete == 'x':
                return
            else:
                element = db.session.execute(db.select(Entry).where(Entry.id == int(toDelete))).scalar_one()
                db.session.delete(element)
        except Exception as e:
            print(f"failed to remove entry, ID may have been entered incorrectly\n{e}\n")
    else:
        print("invalid syntax\n")

def CLIView(command):
    if len(command) == 1:
        if command[0] == 'entries':
            data:list[Entry] = db.session.execute(db.select(Entry).order_by(Entry.name)).scalars().all()
            if len(data) == 0:
                print("no entries in the database\n")
                return
            offset = 0
            ENTRIES_PER_PAGE = 10
            end=False
            while not end:
                print(
                    tabulate.tabulate(
                        [[element.id, element.name, element.locationText, element.locationImg, element.available, element.booked] for element in data[offset:min(offset+ENTRIES_PER_PAGE, len(data))]], 
                        ("id", "name", "location text", "location image", "available", "booked"),
                        maxcolwidths=10
                    ), "\n"
                )
                if len(data) < offset + ENTRIES_PER_PAGE:
                    end = True
                else:
                    end = input(" CATA <e to end> ") == "e"
        elif command[0] == 'bookings':
            data:list[Booking] = db.session.execute(db.select(Booking).order_by(Booking.bookedMaterial)).scalars().all()
            if len(data) == 0:
                print("no entries in the database\n")
                return
            offset = 0
            ENTRIES_PER_PAGE = 5
            end=False
            while not end:
                print(
                    tabulate.tabulate(
                        [[element.id, element.bookedMaterial, element.bookedBy, element.bookInfo] for element in data[offset:min(offset+ENTRIES_PER_PAGE, len(data))]], 
                        ("id", "material", "bokked by", "booking info"),
                        maxcolwidths=10
                    ), "\n"
                )
                if len(data) < offset + ENTRIES_PER_PAGE:
                    end = True
                else:
                    end = input(" CATA <e to end> ") == "e"
        else:
            print("invalid syntax\n")
    else:
        print("invalid syntax\n")

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

# Hello to whoever is editing this in the future
# i have some suggestions for things to add that i couldnt in the time i had. 
# 
#  -  importing + exporting data through Tab Seperated Values
#    This would let you import and export data to and from google sheets, 
#    which might make entering a lot of data a bit easier, especially since
#    the CLI is a bit clunky at the moment

# todo:
#  - booking form
#  - test & improve CLI commands