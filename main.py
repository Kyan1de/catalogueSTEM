# everything exclusively for the website
import logging.config
from flask import Flask, render_template, redirect, url_for, current_app, request
from markupsafe import escape

# for database stuff
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# moving flask's log ouput
import logging
from logging.config import dictConfig

# lets me have the input and server running at the same time
from multiprocessing import Process


# for the command line tool
import tabulate
from typing import Callable
import subprocess

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
    bookedMaterial: Mapped[str] = mapped_column()
    bookedBy: Mapped[str] = mapped_column()
    bookInfo: Mapped[str] = mapped_column()

class MaterialRequest(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    material: Mapped[str] = mapped_column(unique=True)
    requestBy: Mapped[str] = mapped_column()
    info: Mapped[str] = mapped_column()

# handles the web application
app = Flask(__name__)
# connects the database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
# initialize the db with the app
db.init_app(app)

with app.app_context():
    # initializes the database. 
    # if you need to undo this, delete the newly created "instance" folder. 
    # that will delete ALL of the data stored there though, so be careful. 
    # -Kya 2025
    db.create_all()


# --- pages ---
@app.route("/")
@app.route("/index")
def index():
    return render_template('index.html')

@app.route("/db/")
def lookup():
    data: list[Entry] = db.session.execute(db.select(Entry).order_by(Entry.name)).scalars().all()
    return render_template('dbTemplate.html', data=[[entry.name, entry.locationText, entry.locationImg, entry.available, entry.booked] for entry in data])

@app.route("/db/bookings")
def lookupBookings():
    data: list[Booking] = db.session.execute(db.select(Booking).order_by(Booking.bookedBy)).scalars().all()
    return render_template('bookingsTemplate.html', data=[[entry.bookedMaterial, entry.bookedBy, entry.bookInfo] for entry in data])

@app.route("/book/<name>")
def booking(name):
    if request.args:
        mat: Entry = db.session.execute(db.select(Entry).where(Entry.name == name)).scalar_one()
        mat.booked += 1
        db.session.add(Booking(bookedMaterial=name, bookedBy=request.args["name"], bookInfo=request.args["info"]))
        db.session.commit()
        # make page to say booking succeeded
        return app.redirect("/Success")
    else:
        return render_template("bookingTemplate.html", entry=name)

@app.route("/db/requests")
def lookupRequests():
    data: list[MaterialRequest] = db.session.execute(db.select(MaterialRequest).order_by(MaterialRequest.material)).scalars().all()
    return render_template('requestsTemplate.html', data=[[entry.material, entry.requestBy, entry.info] for entry in data])

@app.route("/request")
def makeRequest():
    if request.args:
        try:
            db.session.add(MaterialRequest(material=request.args["material"], requestBy=request.args["name"], info=request.args["info"]))
            db.session.commit()
            return app.redirect("/Success")
        except Exception as e:
            return render_template("fail.html", errorText=e.__repr__())
    else:
        return render_template("requestTemplate.html")

@app.route("/Success")
def success():
    return render_template("success.html")

@app.route("/contributing")
def contributing():
    return render_template("contributing.html")

@app.errorhandler(404)
def pageNotFound(e):
    return render_template("404.html")

# --- handling command-line input. ---
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
        element:Entry = db.session.execute(db.select(Entry).where(Entry.id == int(toDelete))).scalar_one()
        db.session.execute(db.delete(Booking).where(Booking.bookedMaterial == element.name))
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


def CLIAddBooking(command):
    resourceName = input("what are you booking?")
    resource:Entry = db.session.execute(db.select(Entry).where(Entry.name == resourceName)).scalar_one_or_none()
    if resource is None: raise Exception(f"{resourceName} not found in catalogue, please check spelling")
    else:
        bookee = input(f"who is booking the {resourceName}? ")
        info = input("any extra info? ")
        try:
            db.session.add(Booking(bookedMaterial=resourceName, bookedBy=bookee, bookInfo=info))
        except Exception as e:
            print(f"failed to add booking\n{e}\n")

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

def CLIRemoveBooking(command):
    if command[0] == "": raise Exception("invalid syntax, expected name of the entry")
    try:
        elements: list[Booking] = db.session.execute(db.select(Booking).where(Booking.bookedBy.contains(command[0]))).scalars()
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
        element:Booking = db.session.execute(db.select(Booking).where(Booking.id == int(toDelete))).scalar_one()
        entry:Entry = db.session.execute(db.select(Entry).where(Entry.name == element.bookedMaterial)).scalar_one_or_none()
        if entry is not None:
            entry.booked -= 1
        db.session.delete(element)

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
                [[element.id, element.bookedBy, element.bookedMaterial, element.bookInfo] for element in data[offset:min(offset+ENTRIES_PER_PAGE, len(data))]], 
                ("id", "name", "material", "info"),
                maxcolwidths=10
            ), "\n"
        )
        if len(data) < offset + ENTRIES_PER_PAGE:
            end = True
        else:
            end = input(" CATA <e to end> ") == "e"


def CLIAddRequest(command):
    # command is padded with an empty string, so we check for that instead of the length of the command
    if command[0] == "": raise Exception("invalid syntax, expected name of the material. ")
    else:
        resourceName = command[0]
        requestee = input(f"who is requesting the {resourceName}? ")
        info = input("any extra info? (links are helpful) ")
        try:
            db.session.add(MaterialRequest(material=resourceName, requestBy=requestee, info=info))
        except Exception as e:
            print(f"failed to add request\n{e}\n")

def CLIEditRequest(command):
    try:
        elements:list[MaterialRequest] = db.session.execute(db.select(MaterialRequest).where(MaterialRequest.material.contains(command[0]))).scalars()
        print(
            tabulate.tabulate(
                [[element.id, element.material, element.requestBy, element.info] for element in elements], 
                ("id", "material", "booked by", "info"),
                maxcolwidths=10
            ), "\n"
        )
    except Exception as e:
        print("no requests found\n")
        return
    toEdit = ""
    while not toEdit.isdigit() and toEdit != "x":
        toEdit = input("enter the ID of the request to edit (x to cancel): ")
    if toEdit == 'x':
        return
    else:
        element: MaterialRequest = db.session.execute(db.select(MaterialRequest).where(MaterialRequest.id == int(toEdit))).scalar_one()
        info = input("replace info with: ")
        element.info = info

def CLIRemoveRequest(command):
    if command[0] == "": raise Exception("invalid syntax, expected name of the request")
    try:
        elements:list[MaterialRequest] = db.session.execute(db.select(MaterialRequest).where(MaterialRequest.material.contains(command[0]))).scalars()
        print(
            tabulate.tabulate(
                [[element.id, element.material, element.requestBy, element.info] for element in elements], 
                ("id", "material", "booked by", "info"),
                maxcolwidths=10
            ), "\n"
        )
    except Exception as e:
        print("no requests found\n")
        return
    toDelete = ""
    while not toDelete.isdigit() and toDelete != "x":
        toDelete = input("enter the ID of the booking to delete (x to cancel): ")
    if toDelete == 'x':
        return
    else:
        element:MaterialRequest = db.session.execute(db.select(MaterialRequest).where(MaterialRequest.id == int(toDelete))).scalar_one()
        db.session.delete(element)

def CLIViewRequests(command):
    data:list[MaterialRequest] = db.session.execute(db.select(MaterialRequest).order_by(MaterialRequest.material)).scalars().all()
    if len(data) == 0:
        print("no requests in the database\n")
        return
    offset = 0
    ENTRIES_PER_PAGE = 5
    end=False
    while not end:
        print(
            tabulate.tabulate(
                [[element.id, element.material, element.requestBy, element.info] for element in data[offset:min(offset+ENTRIES_PER_PAGE, len(data))]], 
                ("id", "material", "booked by", "info"),
                maxcolwidths=10
            ), "\n"
        )
        if len(data) < offset + ENTRIES_PER_PAGE:
            end = True
        else:
            end = input(" CATA <e to end> ") == "e"


# commands will be called using any tokens not consumed
# as an example: 
#   view entry [options] only passes [options]
#   import [options] only passes [options]
# if something has a default option, it uses the second case
# defaults are optional

# command : {subcommand:func, "default":defaultFunc}
# command : func
commandTable: dict[str, dict[str, Callable] | Callable] = {
    "add" : {"entry":CLIAddEntry, "booking":CLIAddBooking, "request":CLIAddRequest},
    "edit" : {"entry":CLIEditEntry, "booking":CLIEditBooking, "request":CLIEditRequest},
    "remove" : {"entry":CLIRemoveEntry, "booking":CLIRemoveBooking, "request":CLIRemoveRequest},
    "view" : {"entries":CLIViewEntries, "bookings":CLIViewBookings, "requests":CLIViewRequests, "default":CLIViewEntries},
    "commit" : db.session.commit,
    "clear" : (lambda _: print(u"{}[2J{}[;H".format(chr(27), chr(27)), end="")), # evil lambda statement -Kya, 2025
}

#  (both 'args' and 'description' can be empty, 
#   this is just here to add things to the help menu. 
#   nothing here is vital to functioning but do still 
#   add to this when you add things)
# command : [args, description]
helpTable: dict[str, list[str, str]] = {
    # hard-coded commands, dont touch unless you have a good reason
    "help" : ["no arguments", "displays this help message"],
    "quit" : ["no arguments", "exits the program"],

    "add" : ["[entry, booking, request] name", "manually add a row to a table"],
    "edit" : ["[entry, booking, request] name", "edits a row in a table"],
    "remove" : ["[entry, booking, request] name", "manually remove a row from a table"],
    "view" : ["[entries, bookings, requests]", "view the tables from the command line"],
    "commit" : ["no arguments", "save any changes to file, making them visible to the server"],
    "clear" : ["no arguments", "clear the terminal"],
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
                    print(
                        tabulate.tabulate([[command, helpTable[command][0], helpTable[command][1]] for command in helpTable.keys()],
                                          headers=("", "arguments", "description"),
                                          tablefmt="simple"), "\n"
                    )
                elif cmd[0] in commandTable.keys():
                    if type(commandTable[cmd[0]]) is dict:
                        if cmd[1] in commandTable[cmd[0]].keys():
                            commandTable[cmd[0]][cmd[1]](cmd[2:])
                        elif "default" in commandTable[cmd[0]].keys():
                            commandTable[cmd[0]]["default"](cmd[1:])
                    elif callable(commandTable[cmd[0]]):
                        try:
                            commandTable[cmd[0]](cmd[1:])
                        except Exception:
                            commandTable[cmd[0]]()
            except Exception as e:
                # unhelpful? yes. will I make it better? if I have time. 
                print(f"something went wrong, please check your command in the help menu\nrolling back changes to SQL\n{e}\n")
                db.session.rollback()

# --- entry point(s) ---

def runFlask():
    #setup logging
    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }},
        'handlers': {
            'wsgi': {
                'class': 'flaskLogger.myStreamHandler',
                'formatter': 'default'
            },
            'file': {
                'class': 'logging.FileHandler',
                'filename': 'error.log',
                'mode': 'a',
            }},
        'root': {
            'level': 'INFO',
            'handlers': ['wsgi', 'file']
        }
    })
    app.run()

if __name__ == "__main__":
    appProc = Process(target=runFlask)
    appProc.start()
    CLIHandler(appProc)

# --- notes ---

# Hello to whoever is reading this in the future
# I apologize for whatever generational curses you acquired reading my code
# I also hope that the work I have done to make this easier to edit has payed off in the long run
# -Kya, 2025

# oh yeah, when you leave a comment that isnt like... vital documentation, make sure to sign it with -[your first name], [current year]
# this should make it a little easier to keep track of what's documentation and what's convention and stuff. 
# -Kya, 2025