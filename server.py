from flask import Flask, render_template, redirect, url_for, current_app
from markupsafe import escape
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# for debugging reasons
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
    for e in data:
        print(e.__dict__)
    return render_template('dbTemplate.html', data=[[entry.name, entry.locationText, f"{entry.available} / {entry.booked}", "button goes here"] for entry in data])

