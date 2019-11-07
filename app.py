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
    tteid = db.Column(db.String(255), primary_key=True)

class Volunteers(db.Model):
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    role = db.Column(db.String(255))
    hours = db.Column(db.Integer)
    tiers = db.Column(db.String(255))
    slots = db.Column(db.String(255))
    tteid = db.Column(db.String(255), primary_key=True)

class Timeslots(db.Model):
    tteid = db.Column(db.String(255), primary_key=True)
    datetimestart = db.Column(db.DateTime)
    datetimeend = db.Column(db.DateTime)

# -----------------------------------------------------------------------
# Forms
# -----------------------------------------------------------------------
class LoginForm(FlaskForm):
    name = TextField('Name:', validators=[validators.DataRequired()])
    email = TextField('Email:', validators=[validators.DataRequired()])
    password = TextField('Password:', validators=[validators.DataRequired()])

class FileForm(FlaskForm):
    selectfile = SelectField('Filename', validators=[validators.DataRequired()])
    volunteersave = SubmitField(label='Submit')
    volunteerclear = SubmitField(label='Clear All')
    volunteertteupload = SubmitField(label='Upload to TTE')

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
        save_convention(toadd)
        conventions[convention_count]= toadd
        convention_count = convention_count + 1
    return(conventions)

# -----------------------------------------------------------------------
# Pull Convention Data from the TTE API
# -----------------------------------------------------------------------
def tte_convention_api_pull(ttesession,tteconvention_id):
    convention_info = {}
    convention_exist = Conventions.query.get(tteconvention_id)
    if convention_exist is not None:
        # API Pull from TTE to get the convention information and urls needed to process the convention.
        con_params = {'session_id': ttesession, "_include_relationships": 1}
        convention_response = requests.get(config.tte_url + "/convention/" + tteconvention_id, params= con_params)
        convention_data = convention_response.json()
        # API Pull from TTE to get the convention information
        event_params = {'session_id': ttesession, "_include_relationships": 1, '_include': 'hosts'}
        event_response = requests.get('https://tabletop.events' + convention_data['result']['_relationships']['events'], params= event_params)
        event_data = event_response.json()
        for field in event_data['result']['items']:
            slot_url = field['_relationships']['slots']
            event_slots = get_slot_info(ttesession,slot_url)
            field['event_slots'] = event_slots
        # API Pull from TTE to get the volunteer information
        volunteer_params = {'session_id': ttesession}
        volunteer_response = requests.get('https://tabletop.events' + convention_data['result']['_relationships']['volunteers'], params= volunteer_params)
        volunteer_data = volunteer_response.json()
        # Populate dictionary with the info pulled from TTE
        convention_info['event'] = event_data
        convention_info['info'] = convention_exist
        convention_info['data'] = convention_data
        convention_info['volunteers'] = volunteer_data
        return(convention_info)

# -----------------------------------------------------------------------
# Pull Slot Data from the TTE API
# -----------------------------------------------------------------------
def get_slot_info(ttesession,slot_url):
    slot_params = {'session_id': ttesession}
    slot_response = requests.get('https://tabletop.events' + slot_url, params= slot_params)
    slot_data = slot_response.json()
    slot_data = slot_data['result']['items']
    return(slot_data)

# -----------------------------------------------------------------------
# Save Convention information
# -----------------------------------------------------------------------
def save_convention(convention):
    new_convention = Conventions()
    convention_exist = Conventions.query.get(convention['id'])

    if convention_exist is None:
        new_convention.tteid = convention['id']
        new_convention.name = convention['name']
        db.session.merge(new_convention)
        try:
            db.session.commit()
            saved = 'saved'
            return (saved)
        except:
            logger.exception("Cannot save new event")
            db.session.rollback()
            saved = 'failed'
            return (saved)
    else:
        saved = 'exists'
        return (saved)

# -----------------------------------------------------------------------
# Volunteer Functions
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# Ingest Volunteers
# -----------------------------------------------------------------------
def volunteer_parse(filename):
    # Definitions
    volunteer = {}
    newheader = []
    slottimes = []
    all_slots = []

    # Open CSV file and verify headers
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for header in reader.fieldnames:
            if 'Email Address' in header:
                newheader.append('email')
            elif 'Name' in header:
                newheader.append('name')
            elif 'Role' in header:
                newheader.append('role')
            elif 'Hours' in header:
                newheader.append('hours')
            elif 'Tiers' in header:
                newheader.append('tiers')
            elif 'Slot' in header:
                header_l = header.rsplit()
                newheader.append('slot ' + header_l[1])
        reader.fieldnames = newheader
        for vol in reader:
            saved = volunteer_save(vol)
        return(saved)

# -----------------------------------------------------------------------
# Volunteer Save to Database
# -----------------------------------------------------------------------
def volunteer_save(new_volunteer):
    #Declarations
    tiers = []
    header_l = []
    volunteer = Volunteers()
    #
    all_volunteers = list_volunteers()

    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    role = db.Column(db.String(255))
    hours = db.Column(db.Integer)
    tiers = db.Column(db.String(255))
    slots = db.Column(db.String(255))
    tteid = db.Column(db.String(255), primary_key=True)

    try:
        volunteer.name = new_volunteer['name']
        volunteer.email = new_volunteer['email']
        volunteer.emergency_info = new_volunteer['emergency_info']
        volunteer.role = new_volunteer['role']
    except:
        pass
    try:
        if 'Tier 1' in new_volunteer['tiers']:
            tiers.append('1')
        if 'Tier 2' in new_volunteer['tiers']:
            tiers.append('2')
        if 'Tier 3' in new_volunteer['tiers']:
            tiers.append('3')
        if 'Tier 4' in new_volunteer['tiers']:
            tiers.append('4')
        volunteer.tiers = ','.join(tiers)
    except:
        pass
    try:
        if new_volunteer['hours'] == 'badge':
            volunteer.hours = 12
        if new_volunteer['hours'] == 'hotel':
            volunteer.hours = 20
        if int(new_volunteer['hours']):
            volunteer.hours = new_volunteer['hours']
    except:
        pass
    for volunteer_header,volunteer_info in new_volunteer:
        if 'slot' in volunteer_header:
            header_l = volunteer_header.rsplit()
            if 'X' in volunteer_info:
                all_slots.append(header_l)
        volunteer.slot_pref = all_slots
    db.session.merge(volunteer)
    try:
        db.session.commit()
        #session.permanent = True
        saved = 'saved'
        return (saved)
    except:
        logger.exception("Cannot save volunteer")
        db.session.rollback()
        saved = 'failed'
        return ()

# -----------------------------------------------------------------------
# List all volunteers in database
# -----------------------------------------------------------------------
def list_volunteers():
    volunteer = Volunteers()

    all_volunteers = Volunteers.query.order_by(volunteer.id).all()
    return(all_volunteers)


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
# Allow only CSV files
# -----------------------------------------------------------------------
def allowed_file(filename):
    extensions=config.ALLOWED_EXTENSIONS

    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in extensions

# -----------------------------------------------------------------------
# Index Route
# -----------------------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def index():

    # Check to see if the user already exists.
    # If it does, pass the user's name to the render_template
    if 'name' in session:
        name = session.get('name')
        ttesession = session.get('ttesession')
        return render_template('base.html', **{'name' : name})
    else:
    #Otherwose, just load the page.  Page has code to detect if name exists
        return render_template('base.html')

# -----------------------------------------------------------------------
# Upload file Route
# -----------------------------------------------------------------------
@app.route('/upload', methods=['GET', 'POST'])
# Display a visual to upload a CSV file.
def upload():
    folder=config.UPLOAD_FOLDER

    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(folder, filename))
            return render_template('upload.html', filename=filename)
    return render_template('upload.html')

# -----------------------------------------------------------------------
# Conventions Route
# -----------------------------------------------------------------------
@app.route('/conventions', methods=['GET', 'POST'])
def conventions():
    # Declarations
    tteconvention_info = {}
    name = session.get('name')
    ttesession = session.get('ttesession')
    tteconvention_info = None
    folder = config.UPLOAD_FOLDER
    files = os.listdir(folder)
    # Form Declarations
    fileform = FileForm(request.form, obj=files)
    fileform.selectfile.choices = [(file,file) for file in files]
    # Function calls
    tteconventions = gettteconventions(ttesession)
    if request.method == "POST":
        tteconvention_id = request.form.get("conventions", None)
        if tteconvention_id !=None:
            # Pull all the data regarding the convention
            tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)

            if fileform.validate_on_submit:
                # Volunteer Management
                select = request.form.get('selectfile')
                location = os.path.join(folder,select)
                print (request.form.get('submit'))
                if 'volunteersave' in request.form.get('submit'):

#                   saved = volunteer_parse(location)
                    return render_template('conventions.html', fileform=fileform, **{'name' : name,
                    'tteconventions' : tteconventions,
                    'tteconvention_data' : tteconvention_data
                    })
            return render_template('conventions.html', fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_data' : tteconvention_data
            })
    else:
        return render_template('conventions.html', fileform=fileform, **{'name' : name,
        'tteconventions' : tteconventions
        })
# -----------------------------------------------------------------------
# Run Program
# -----------------------------------------------------------------------
if __name__ == '__main__':
    app.run(port=config.PORT, host=config.HOST)
