from flask import Flask
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask import flash
from flask import send_from_directory
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import TextField, PasswordField, TextAreaField, validators, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm.exc import NoResultFound

import os
import shutil
from pathlib import Path
import logging
import calendar
import config
import random
import datetime
import time
import re
import csv
import json
import requests

# logger stuff
logger = logging.getLogger(__name__)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(formatter)
logger.addHandler(console)

# init app and load conf
app = Flask(__name__, static_url_path='/templates')
app.config.from_object(config)
csrf = CSRFProtect(app)

# init db
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# -----------------------------------------------------------------------
# Database models
# -----------------------------------------------------------------------
class Conventions(db.Model):
    name = db.Column(db.String(255))
    tteuri = db.Column(db.String(255))
    tteid = db.Column(db.String(255), primary_key=True)

class Volunteers(db.Model):
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    slot_pref = db.Column(db.String(512))
    tteuri = db.Column(db.String(255))
    tteid = db.Column(db.String(255), primary_key=True)

class Slots(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetimestart = db.Column(db.DateTime)
    datetimeend = db.Column(db.DateTime)

class Events(db.Model):
    code = db.Column(db.String(255))
    title = db.Column(db.String(255))
    length = db.Column(db.Integer)
    description = db.Column(db.String(1024))
    tier = db.Column(db.Integer)
    tteuri = db.Column(db.String(255))
    tteid = db.Column(db.String(255), primary_key=True)

class Tables(db.Model):
    tteid = db.Column(db.String(255), primary_key=True)

# -----------------------------------------------------------------------
# Forms
# -----------------------------------------------------------------------
class LoginForm(FlaskForm):
    name = TextField('Name:', validators=[validators.DataRequired()])
    email = TextField('Email:', validators=[validators.DataRequired()])
    password = TextField('Password:', validators=[validators.DataRequired()])

class SlotForm(FlaskForm):
    number = TextField('Slot Number', validators=[validators.optional()])
    year = SelectField('Year:', coerce=int, validators=[validators.optional()])
    month = SelectField('Month:', coerce=str, validators=[validators.optional()])
    day = SelectField('Day:', coerce=int, validators=[validators.optional()])
    length = TextField('Length:', validators=[validators.optional()])
    time = TextField('Time:', validators=[validators.optional()])
    submit = SubmitField(label='Submit')
    clear = SubmitField(label='Clear All Slots')
    delete = SubmitField(label='Delete')

    def reset(self):
        blankData = MultiDict([ ('csrf', self.reset_csrf() ) ])
        self.process(blankData)

class TableForm(FlaskForm):
    number = TextField('Table Number', validators=[validators.optional()])
    players = TextField('Number of Players:', validators=[validators.optional()])
    bulk_tables = TextField('Number of Tables:', validators=[validators.optional()])
    bulk_players = TextField('Number of Players:', validators=[validators.optional()])
    submit = SubmitField(label='Submit')
    clear = SubmitField(label='Clear All Tables')
    bulk_add = SubmitField(label='Add Multiple Tables')

    def reset(self):
        blankData = MultiDict([ ('csrf', self.reset_csrf() ) ])
        self.process(blankData)

class EventForm(FlaskForm):
    number = TextField('Table Number', validators=[validators.DataRequired()])
    code = TextField('Adventure Code', validators=[validators.DataRequired()])
    title = TextField('Adventure Code', validators=[validators.DataRequired()])
    length = TextField('Adventure Code', validators=[validators.DataRequired()])
    description = TextAreaField('Adventure Code', validators=[validators.DataRequired()])
    tier = TextField('Adventure Code', validators=[validators.DataRequired()])
    submit = SubmitField(label='Submit')
    clear = SubmitField(label='Clear All Slots')

    def reset(self):
        blankData = MultiDict([ ('csrf', self.reset_csrf() ) ])
        self.process(blankData)

class SessionForm(FlaskForm):
    table = SelectField('Table', coerce=int)
    slot = SelectField('Slot', coerce=int)
    volunteer = SelectField('Volunteer', coerce=int)
    event = SelectField('Event', coerce=str)
    session_info = SubmitField(label='Submit')
    delete = SubmitField(label='Delete Sessions')

class SessionDeleteForm(FlaskForm):
    sessions = SelectField('Session', coerce=str)
    delete = SubmitField(label='Delete Slots')

class FileForm(FlaskForm):
    selectfile = SelectField('Filename', validators=[validators.DataRequired()])
    submit = SubmitField(label='Submit')
    clear = SubmitField(label='Clear All Slots')

# -----------------------------------------------------------------------
# Internal Functions
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# Start a Session to TTE
# -----------------------------------------------------------------------
def tte_session():
    params = {'api_key_id': config.tte_api_key_id, 'username' : config.tte_username, 'password': config.tte_password}
    response = requests.post(config.tte_url + "/session", params=params)
    if response.status_code==200:
        session = response.json()['result']
    return (session)

# -----------------------------------------------------------------------
# Pull Convention listing from TTE
# -----------------------------------------------------------------------
def gettteconventions(ttesession):
    params = {'session_id': ttesession['id']}
    response = requests.get(config.tte_url + "/group/" + config.tte_group_id + "/conventions", params=params)
    data = response.json()
    convention_count = 0
    conventions = {}
    for convention in data['result']['items']:
        toadd = {'name': convention['name'], 'id': convention['id']}
        conventions[convention_count]= toadd
        convention_count = convention_count + 1
    return(conventions)

# -----------------------------------------------------------------------
# Pull Convention listing from TTE
# -----------------------------------------------------------------------
def newconventionfile(tteconventions,ttesession):
    con_name = tteconventions['name']
    con_id = tteconventions['id']
    con_events = tte_convention_api_pull(ttesession,con_name,con_id)
    dst = "templates/" + con_name + ".html"
    src = ("templates/newconventionbase.html")
    shutil.copy(src,dst)
    return()

# -----------------------------------------------------------------------
#
# -----------------------------------------------------------------------
def tte_convention_api_pull(ttesession,con_name,con_id):
    params = {'session_id': ttesession, "_include_relationships": 1}
    con_response = requests.get(config.tte_url + "/convention/" + con_id, params=params)
    con_data = con_response.json()
    print(con_data)
    print("---Convention---")
    print(con_name)
    print("---Event Listing---")
    event_response = requests.get('https://tabletop.events' + con_data['result']['_relationships']['events'], params=params)
    event_data = event_response.json()
    for field in event_data['result']['items']:
        print (field)
#        print (field['name'],field['_relationships']['eventhosts'])
    return(event_data)

# -----------------------------------------------------------------------
# Login to server route
# -----------------------------------------------------------------------
# This is a rudimentary authentication scheme.  A more robuest auth setup will be implemented before I do final release.
@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm(request.form)
    session['id'] = 0

    if request.method == 'POST':
        name = request.form['name']
        user = request.form['email'] #
        password = request.form['password']

        if form.validate():
            if 'Eric' in name:
                session['name'] = name
                session['ttesession'] = tte_session()
                return redirect(url_for('index'))
            else:
                flash('Please enter a valid user')
                return redirect(request.url)
        else:
            flash('All the form fields are required.')
            return redirect(request.url)
    return render_template('login.html', form=form)

# -----------------------------------------------------------------------
# Index Route
# -----------------------------------------------------------------------
@app.route('/')
def index():
    # Check to see if the user already exists.
    # If it does, pass the user's name to the render_template
    if 'name' in session:
        name = session.get('name')
        ttesession = session.get('ttesession')
        tteconventions = gettteconventions(ttesession)
        for convention in tteconventions:
            if os.path.isfile('templates/' + tteconventions[convention]['name'] + '.html') is False:
                newconvention = newconventionfile(tteconventions[convention],ttesession)
        return render_template('base.html', **{'name' : name, 'tteconventions' : tteconventions})
    else:
    #Otherwose, just load the page.  Page has code to detect if name exists
        return render_template('base.html')

# -----------------------------------------------------------------------
# Convention Page Routes
# -----------------------------------------------------------------------
@app.route('/<convention>')
def tte(convention):
    name = session.get('name')
    file = convention + '.html'
    return render_template(file, **{'name' : name, 'ttecon' : convention})

# -----------------------------------------------------------------------
# Run Program
# -----------------------------------------------------------------------
if __name__ == '__main__':
    app.run(port=config.PORT, host=config.HOST)
