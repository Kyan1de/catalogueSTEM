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

# for the command line tool
import tabulate
from typing import Callable

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

def CLIAddEntry(command):
    # command is padded with an empty string, so we check for that instead of the length of the command
    if command[0] == "": raise Exception("invalid syntax, expected name of the entry. ")
    locationText = input(f"describe the location of the '{command[0]}': ")
    locationImg = input("enter the file name of the image showing its location: ")
    available = int(input(f"how many '{command[0]}'s are there: "))
    try:
        db.session.add(Entry(name=command[0], locationText=locationText, locationImg=locationImg, available=available, booked=0))
    except Exception as e:
        print(f"failed to add entry, it may already exist\n{e}\n")

def CLIAddBooking(command):
    resourceName = input("what are you booking?")
    resource:Entry = db.session.execute(db.select(Entry).where(Entry.name == resourceName)).scalar_one_or_none()
    if resource is None: raise Exception(f"{resourceName} not found in catalogue, please check spelling")
    elif resource.booked == resource.available: raise Exception(f"{resourceName} has been fully booked, try again later")
    else:
        bookee = input(f"who is booking the {resourceName}? ")
        info = input("any extra info? ")
        try:
            db.session.add(Booking(bookedMaterial=resourceName, bookedBy=bookee, bookInfo=info))
        except Exception as e:
            print(f"failed to add booking\n{e}\n")

def CLIEditEntry(command):
    if len(command) != 2: raise Exception("invalid syntax, expected the name of the entry and the info you wanted to change\n('locationText', 'locationImg', or 'count')")
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
        return
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

def CLIEditBooking(command):
    if len(command) != 2: raise Exception("invalid syntax, expected the name of the booking and the info you wanted to change\n('name' or 'info')")
    if command[1] not in ["name","info"]: raise Exception("invalid attribute") 
    try:
        elements:list[Booking] = db.session.execute(db.select(Booking).where(Booking.bookedBy.contains(command[0]))).scalars()
        print(
            tabulate.tabulate(
                [[element.id, element.bookedBy, element.bookedMaterial, element.bookInfo] for element in elements], 
                ("id", "name", "material", "info"),
                maxcolwidths=10
            ), "\n"
        )
    except Exception as e:
        print("no bookings found\n")
        return
    toEdit = ""
    while not toEdit.isdigit() and toEdit != "x":
        toEdit = input("enter the ID of the entry to edit (x to cancel): ")
    if toEdit == 'x':
        return
    else:
        element: Booking = db.session.execute(db.select(Booking).where(Booking.id == int(toEdit))).scalar_one()
        if command[1] == "name": input(f"name of person booking {element.bookedMaterial}: ")
        if command[1] == "info": input(f"info for the booking: ")

def CLIRemoveEntry(command):
    if command[0] == "": raise Exception("invalid syntax, expected name of the entry")
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
        print(f"no entries found\n")
        return

    toDelete = ""
    while not toDelete.isdigit() and toDelete != "x":
        toDelete = input("enter the ID of the entry to delete (x to cancel): ")
    if toDelete == 'x':
        return
    else:
        element = db.session.execute(db.select(Entry).where(Entry.id == int(toDelete))).scalar_one()
        db.session.delete(element)

def CLIRemoveBooking(command):
    if command[0] == "": raise Exception("invalid syntax, expected name of the entry")
    try:
        elements: list[Booking] = db.session.execute(db.select(Booking).where(Booking.name.contains(command[0]))).scalars()
        print(
            tabulate.tabulate(
                [[element.id, element.bookedBy, element.bookedMaterial, element.bookInfo] for element in elements], 
                ("id", "name", "material", "info"),
                maxcolwidths=10
            ), "\n"
        )
    except Exception as e:
        print(f"no entries found\n")
        return
        
    toDelete = ""
    while not toDelete.isdigit() and toDelete != "x":
        toDelete = input("enter the ID of the booking to delete (x to cancel): ")
    if toDelete == 'x':
        return
    else:
        element = db.session.execute(db.select(Booking).where(Booking.id == int(toDelete))).scalar_one()
        db.session.delete(element)

def CLIViewEntries(command):
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

def CLIViewBookings(command):
    data:list[Booking] = db.session.execute(db.select(Booking).order_by(Booking.bookedMaterial)).scalars().all()
    if len(data) == 0:
        print("no bookings in the database\n")
        return
    offset = 0
    ENTRIES_PER_PAGE = 5
    end=False
    while not end:
        print(
            tabulate.tabulate(
                [[element.id, element.bookedBy, element.bookedMaterial, element.bookInfo] for element in elements], 
                ("id", "name", "material", "info"),
                maxcolwidths=10
            ), "\n"
        )
        if len(data) < offset + ENTRIES_PER_PAGE:
            end = True
        else:
            end = input(" CATA <e to end> ") == "e"

# commands will be called using any tokens not consumed
#   view entry [options] only passes [options]
#   import [options] only passes [options] (NOT YET IMPLEMENTED)
# if something has a default option, it uses the second case
# defaults are optional

# command : {subcommand:func, "default":defaultFunc}
# command : func
commandTable: dict[str, dict[str, Callable] | Callable] = {
    "add" : {"entry":CLIAddEntry, "booking":CLIAddBooking},
    "remove" : {"entry":CLIRemoveEntry, "booking":CLIRemoveBooking},
    "view" : {"entries":CLIViewEntries, "bookings":CLIViewBookings},
    "commit": db.session.commit
}

def CLIHandler(appProc: Process):
    with app.app_context():
        while True:
            userInput = input(" CATA > ").rstrip().lstrip()
            cmd = userInput.split()
            cmd.append("") # append an empty string to pad the end, for commands that dont take args
            try: 
                if userInput.lower() == "quit":
                    print("shutting down...")
                    print("(you may need to manually close the logging window)")
                    appProc.kill()
                    appProc.join()
                    appProc.close()
                    quit()
                elif userInput.lower() == "help":
                    print("if this message is still here, bug Kya about it\n") # do this later
                elif cmd[0] in commandTable.keys():
                    if type(commandTable[cmd[0]]) is dict:
                        if cmd[1] in commandTable[cmd[0]].keys():
                            commandTable[cmd[0]][cmd[1]](cmd[2:])
                        elif "default" in commandTable[cmd[0]].keys():
                            commandTable[cmd[0]]["default"](cmd[1:])
                    elif type(commandTable[cmd[0]]) is Callable:
                        try:
                            commandTable[cmd[0]](cmd[1:])
                        except Exception:
                            commandTable[cmd[0]]()
            except Exception as e:
                # unhelpful? yes. will I make it better? if I have time. 
                print(f"something went wrong, please check your command in the help menu\nrolling back changes to SQL\n{e}\n")
                db.session.rollback()

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