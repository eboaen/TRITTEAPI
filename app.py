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
from wtforms.widgets import TextArea
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm.exc import NoResultFound
from pytz import timezone

import pytz
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
from collections import OrderedDict
#Debugging Tools
import inspect

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

# init global
tteconvention_data = {}


# -----------------------------------------------------------------------
#  Classes
# -----------------------------------------------------------------------
class Convention:
    def __init__(self, name):
        self.name = name
    def add_location(self, geolocation_name):
        self.location = geolocation_name
    def add_description(self, description):
        self.description = description
    def add_phone_number(self, phone_number):
        self.phone_number = phone_number
    def add_email(self, email):
        self.email = email
    def add_dates(self, dates):
        self.dates = dates

# -----------------------------------------------------------------------
# Database models
# -----------------------------------------------------------------------
class Conventions(db.Model):
    name = db.Column(db.String(255))
    tteid = db.Column(db.String(255), primary_key=True)
    slots = db.Column(db.String(2048))
    tables = db.Column(db.String(255))

class Volunteers(db.Model):
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    role = db.Column(db.String(255))
    hours = db.Column(db.Integer)
    tiers = db.Column(db.String(255))
    slots = db.Column(db.String(255))
    conventions = db.Column(db.String(255))
    tteid = db.Column(db.String(255), primary_key=True)

# -----------------------------------------------------------------------
# Forms
# -----------------------------------------------------------------------
class LoginForm(FlaskForm):
    name = StringField('Name:', validators=[validators.DataRequired()])
    email = StringField('Email:', validators=[validators.DataRequired()])
    password = StringField('Password:', validators=[validators.DataRequired()])

class FileForm(FlaskForm):
    selectfile = SelectField('Filename', validators=[validators.DataRequired()])
    volunteersave = SubmitField(label='Submit File for Volunteers')
    eventsave = SubmitField(label='Submit File for Convention Events')
    conventionsave = SubmitField(label='Submit File for Convention Details')
    eventsdelete = SubmitField(label='Delete All Convention Events')
    shiftsdelete = SubmitField(label='Delete All Volunteer Shifts ')
    daypartsdelete = SubmitField(label='Delete All Convention Day Parts')
    roomsandtablesdelete = SubmitField(label='Delete All Convention Rooms and Tables')

class ConForm(FlaskForm):
    selectcon = SelectField('Convention', validators=[validators.DataRequired()])
    consubmit = SubmitField(label='Submit')

class LogoutForm(FlaskForm):
    logoutsubmit = SubmitField(label='Logout')

class NewConventionForm(FlaskForm):
    name = StringField('New Convention Name:', validators=[validators.DataRequired()])
    location = StringField('City, State of the Convention:', validators=[validators.DataRequired()])
    description = TextAreaField('Description of the Convention:', widget=TextArea(), validators=[validators.DataRequired()])
    phone_number = StringField('Please provide your phone number for volunteers to contact you: ', validators=[validators.DataRequired()])
    email = StringField('Please provide your email for volunteers to contact you: ', validators=[validators.DataRequired()])
    dates = TextAreaField('List each date of the Convention, one date per line:', widget=TextArea(), validators=[validators.DataRequired()])
    conventionsubmit = SubmitField(label='Submit')

# -----------------------------------------------------------------------
# Internal Functions
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# Convert a given datetime object to a UTC time
# -----------------------------------------------------------------------
def datetime_utc_convert(ttesession,tteconvention_id,unconverted_datetime):
    timezone_data = tte_convention_geolocation_api_get(ttesession,tteconvention_id)
    current_tz = timezone(timezone_data)
    dt = current_tz.localize(unconverted_datetime)
    utc_delta = dt.utcoffset()
    utc_time = unconverted_datetime - utc_delta
    return(utc_time)

# -----------------------------------------------------------------------
# Convert UTC datetime object to the convention time
# -----------------------------------------------------------------------
def datetime_timezone_convert(ttesession,tteconvention_id, utc_datetime):
    timezone_data = tte_convention_geolocation_api_get(ttesession,tteconvention_id)
    current_tz = timezone(timezone_data)
    utc_tz = timezone('UTC')
    current_time = utc_tz.localize(utc_datetime).astimezone(current_tz)
    return(current_time)

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
# Create the updateconform object to display pre-existing data for a convention
# -----------------------------------------------------------------------
def conform_info():
    all_days = []
    #Create and populate a new instance of the Convention class
    this_convention = Convention(tteconvention_data['result']['name'])
    this_convention.add_location(tteconvention_data['result']['geolocation_name'])
    this_convention.add_phone_number(tteconvention_data['result']['phone_number'])
    this_convention.add_email(tteconvention_data['result']['email_address'])
    this_convention.add_description(tteconvention_data['result']['description'])
    for day in tteconvention_data['result']['days']:
        dayonly = day['day_time'].strftime('%m/%d/%Y')
        all_days.append(dayonly)
    this_convention.add_dates(all_days)
    updateconform = NewConventionForm(request.form, obj=this_convention)
    updateconform.populate_obj(this_convention)
    return(updateconform)


# -----------------------------------------------------------------------
# Convention Functions
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# Pull Convention listing from TTE for TRI
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
# Pull Convention Data from the TTE API
# -----------------------------------------------------------------------
def tte_convention_api_get(ttesession,tteconvention_id):
    # print ('tte_convention_api_get testing')
    # Call the global so we can modify it in the function
    global tteconvention_data
    convention_info = {}
    # API Pull from TTE to get the convention information and urls needed to process the convention.
    con_params = {'session_id': ttesession['id'], '_include_relationships': 1, '_include': 'description', '_include': 'volunteer_custom_fields'}
    convention_response = requests.get(config.tte_url + "/convention/" + tteconvention_id, params= con_params)
    tteconvention_data = convention_response.json()
    # API Pull from TTE to get the external json information
    con_jparams = {'session_id': ttesession['id']}
    convention_jresponse = requests.get(config.tte_url + "/convention/" + tteconvention_id + '/external_jsons', params= con_jparams)
    convention_jjson = convention_jresponse.json()
    tteconvention_data['result']['external_jsons'] = convention_jjson['result']['items']
    # API Pull from TTE to get
    event_data = tte_events_api_get(ttesession,tteconvention_id)
    for event in event_data:
        # Get the slots this event is assigned to
        slots_url = 'https://tabletop.events' + event['_relationships']['slots']
        event_slots = tte_event_slots_api_get(ttesession,tteconvention_id,slots_url)
        slot_tables = slots_parse(event_slots)
        print (event['event_number'],event['name'])
        event['event_tables'] = slot_tables
        # Get the hosts this event has
        # hosts_url = field['_relationships']['hosts']
        # event_hosts = tte_event_hosts_api_get(ttesession,tteconvention_id,hosts_url)
        # field['event_hosts'] = event_hosts
    # API Pull from TTE to get the volunteer information
    volunteer_data = tte_convention_volunteer_api_get(ttesession,tteconvention_id)
    # Populate dictionary with the info pulled from TTE
    tteconvention_data['result']['geolocation_name'] = tte_geolocation_byid_api_get(ttesession)
    tteconvention_data['result']['days'] = tte_convention_days_api_get(ttesession,tteconvention_id)
    tteconvention_data['events'] = event_data
    tteconvention_data['volunteers'] = volunteer_data
    return()

# -----------------------------------------------------------------------
# Create a new Convention
# -----------------------------------------------------------------------
def tte_convention_convention_api_post(ttesession,new_convention):
    print ('debug tte_convention_convention_api_post')
    # Declarations
    # Function Calls
    geolocation_id = tte_geolocation_api_get(ttesession,new_convention)
    # Define parameters to create the convention
    convention_url = '/api/convention'
    convention_params = {
                        'session_id': ttesession['id'],
                        'website_uri': 'https://theroleinitiative.org',
                        'name': new_convention['name'],
                        'description': new_convention['description'],
                        'facebook_page': 'https://www.facebook.com/theroleinitiative/',
                        'generic_ticket_price': 0,
                        'group_id': config.tte_group_id,
                        'slot_duration': 30,
                        'twitter_handle': '@_roleinitiative',
                        'email_address': 'events@theroleinitiative.org',
                        'phone_number': new_convention['phone_number'],
                        'geolocation_id': geolocation_id,
                        'volunteer_management': 'enabled',
                        '_include_relationships':1
                        }
    convention_response = requests.post('https://tabletop.events' + convention_url, params= convention_params)
    convention_json = convention_response.json()
    print (convention_json)
    tteconvention_id = convention_json['result']['id']
    # Create each day of the convention
    tte_convention_days_api_post(ttesession,tteconvention_id,new_convention)
    # Due to how TTE handles the Volunteer Custom Fields, after the convention is created we have to get the id of the json object, then append those fields via the randomized endpoint id.
    con_jparams = {'session_id': ttesession['id']}
    convention_jresponse = requests.get(config.tte_url + "/convention/" + tteconvention_id + '/external_jsons', params= con_jparams)
    print (convention_jresponse.url)
    convention_jjson = convention_jresponse.json()
    print(convention_jjson)
    # Find the json object for the "volunteer_custom_fields"
    for object in convention_jjson['result']['items']:
        if object['name'] == 'volunteer_custom_fields':
            # Get the id of the object
            tteconvention_volunteer_custom_fields_id = object['id']
    convention_externaljson_params = {
                        'session_id': ttesession['id'],
                        'json': [
                            {
                                "required" : "1",
                                "label" : "Emergency Contact: Name, phone number, relationship",
                                "name" : "volunteeremergencycontact",
                                "edit" : "0",
                                "type" : "text",
                                "conditional" : "0",
                                "view" : "1",
                                "sequence_number" : "3"
                             },
                             {
                                "required" : "0",
                                "label" : "Previous Convention/D&D Volunteer experience",
                                "type" : "textarea",
                                "conditional" : "0",
                                "name" : "volunteerexperience",
                                "edit" : "0",
                                "sequence_number" : "2",
                                "view" : "1"
                             },
                             {
                                "view" : "1",
                                "sequence_number" : "4",
                                "edit" : "0",
                                "name" : "volunteerlevel",
                                "type" : "select",
                                "conditional" : "0",
                                "options" : "Hotel\n4 Day\n1 day\n1 slot",
                                "label" : "Volunteer Level - Hotel level requires committing to 24 hours over the 4 days of the convention.  Badge Level requires 12 hours, Day level requires 4 hours.  1 slot is 2 hours.  At this time we cannot confirm Hotels Slots will be available for the convention, but if you are interested in volunteering at that level still select that as an option please.",
                                "required" : "1"
                             },
                             {
                                "required" : "0",
                                "label" : "Shirt Size",
                                "options" : "S\nM\nL\nXL\nXXL\n3X\n4X\n5X",
                                "type" : "select",
                                "conditional" : "0",
                                "name" : "volunteershirtsize",
                                "edit" : "0",
                                "view" : "1",
                                "sequence_number" : "7"
                             },
                             {
                                "label" : "Other comments (accommodations requests, allergies we should be aware of, other things you feel you should share, etc.)",
                                "required" : "0",
                                "type" : "textarea",
                                "conditional" : "0",
                                "edit" : "0",
                                "name" : "volunteerother",
                                "sequence_number" : "11",
                                "view" : "1"
                             },
                             {
                                "sequence_number" : "9",
                                "view" : "1",
                                "conditional" : "0",
                                "type" : "text",
                                "edit" : "0",
                                "name" : "volunteerlocation",
                                "label" : "Where are you coming from (City/State)",
                                "required" : "1"
                             },
                             {
                                "view" : "1",
                                "sequence_number" : "1",
                                "required" : "0",
                                "label" : "What pronouns do you use for yourself?",
                                "name" : "volunteerpronouns",
                                "edit" : "0",
                                "conditional" : "0",
                                "type" : "text"
                             },
                             {
                                "sequence_number" : "8",
                                "view" : "1",
                                "edit" : "0",
                                "name" : "volunteersource",
                                "conditional" : "0",
                                "type" : "text",
                                "label" : "How did you hear about us?",
                                "required" : "1"
                             },
                             {
                                "options" : "None\n1\n2\n3\n4",
                                "required" : "1",
                                "label" : "Tier (What is the highest Tier you are comfortable GMing, enter None if you do not want to GM at all)",
                                "name" : "volunteertiers",
                                "edit" : "0",
                                "conditional" : "0",
                                "type" : "select",
                                "sequence_number" : "6",
                                "view" : "1"
                             },
                             {
                                "sequence_number" : "10",
                                "view" : "1",
                                "conditional_name" : "volunteerlevel",
                                "edit" : "0",
                                "conditional_value" : "Hotel",
                                "name" : "volunteerhotelpref",
                                "conditional" : "1",
                                "type" : "select",
                                "options" : "Male\nFemale\nAny",
                                "label" : "Hotel Rooming Preference",
                                "required" : "0"
                             },
                             {
                                "view" : "1",
                                "sequence_number" : "5",
                                "required" : "1",
                                "label" : "What role are you interested in?  Admin roles are as follows: Runners work with the Admins assigned to the slot, they will help GMs with getting their badges and perform health checks.  Admins will help seat players at tables and check DMs in.  Head admin will be the escalation point for any issues that arise.",
                                "options" : "DM - Adventurers League Only\nDM - Acquisitions Incorporated Only\nDM - Any\nAdmin\nAny",
                                "conditional" : "0",
                                "type" : "select",
                                "name" : "volunteerrole",
                                "edit" : "0"
                             }
                         ]
                        }
    convention_externaljson_response = requests.put('https://tabletop.events/api/conventionjson/' + tteconvention_volunteer_custom_fields_id, params= convention_externaljson_params)
    convention_externaljson_json = convention_externaljson_response.json()
    print (convention_externaljson_json)
    return(tteconvention_id)

# -----------------------------------------------------------------------
# Update a Convention
# -----------------------------------------------------------------------
def tte_convention_convention_api_put(ttesession,update_convention):
    geolocation_id = tte_geolocation_api_get(ttesession,update_convention)
    convention_url = '/api/convention/' + tteconvention_data['result']['id']
    convention_params = {
                        'session_id': ttesession['id'],
                        'name': update_convention['name'],
                        'phone_number': update_convention['phone_number'],
                        'email_address': update_convention['email'],
                        'geolocation_id': geolocation_id,
                        'description': update_convention['description']
                        }
    convention_response = requests.put('https://tabletop.events' + convention_url, params= convention_params)
    convention_json = convention_response.json()
    print (convention_json)
    return()

# -----------------------------------------------------------------------
# Update an existing Convention with TRI standard information
# -----------------------------------------------------------------------
def tte_convention_convention_tristandard_api_put(ttesession):
    print ('debug tte_convention_convention_tristandard_api_put')
    # Declarations
    # Define parameters to update the convention
    convention_url = 'https://tabletop.events/api/convention/' + tteconvention_data['result']['id']
    convention_params = {
                        'session_id': ttesession['id'],
                        'volunteer_custom_fields': [
                            {
                                "required" : "1",
                                "label" : "Emergency Contact: Name, phone number, relationship",
                                "name" : "volunteeremergencycontact",
                                "edit" : "0",
                                "type" : "text",
                                "conditional" : "0",
                                "view" : "1",
                                "sequence_number" : "3"
                             },
                             {
                                "required" : "0",
                                "label" : "Previous Convention/D&D Volunteer experience",
                                "type" : "textarea",
                                "conditional" : "0",
                                "name" : "volunteerexperience",
                                "edit" : "0",
                                "sequence_number" : "2",
                                "view" : "1"
                             },
                             {
                                "view" : "1",
                                "sequence_number" : "4",
                                "edit" : "0",
                                "name" : "volunteerlevel",
                                "type" : "select",
                                "conditional" : "0",
                                "options" : "Hotel\n4 Day\n1 day\n1 slot",
                                "label" : "Volunteer Level - Hotel level requires committing to 24 hours over the 4 days of the convention.  Badge Level requires 12 hours, Day level requires 4 hours.  1 slot is 2 hours.  At this time we cannot confirm Hotels Slots will be available for the convention, but if you are interested in volunteering at that level still select that as an option please.",
                                "required" : "1"
                             },
                             {
                                "required" : "0",
                                "label" : "Shirt Size",
                                "options" : "S\nM\nL\nXL\nXXL\n3X\n4X\n5X",
                                "type" : "select",
                                "conditional" : "0",
                                "name" : "volunteershirtsize",
                                "edit" : "0",
                                "view" : "1",
                                "sequence_number" : "7"
                             },
                             {
                                "label" : "Other comments (accommodations requests, allergies we should be aware of, other things you feel you should share, etc.)",
                                "required" : "0",
                                "type" : "textarea",
                                "conditional" : "0",
                                "edit" : "0",
                                "name" : "volunteerother",
                                "sequence_number" : "11",
                                "view" : "1"
                             },
                             {
                                "sequence_number" : "9",
                                "view" : "1",
                                "conditional" : "0",
                                "type" : "text",
                                "edit" : "0",
                                "name" : "volunteerlocation",
                                "label" : "Where are you coming from (City/State)",
                                "required" : "1"
                             },
                             {
                                "view" : "1",
                                "sequence_number" : "1",
                                "required" : "0",
                                "label" : "What pronouns do you use for yourself?",
                                "name" : "volunteerpronouns",
                                "edit" : "0",
                                "conditional" : "0",
                                "type" : "text"
                             },
                             {
                                "sequence_number" : "8",
                                "view" : "1",
                                "edit" : "0",
                                "name" : "volunteersource",
                                "conditional" : "0",
                                "type" : "text",
                                "label" : "How did you hear about us?",
                                "required" : "1"
                             },
                             {
                                "options" : "None\n1\n2\n3\n4",
                                "required" : "1",
                                "label" : "Tier (What is the highest Tier you are comfortable GMing, enter None if you do not want to GM at all)",
                                "name" : "volunteertiers",
                                "edit" : "0",
                                "conditional" : "0",
                                "type" : "select",
                                "sequence_number" : "6",
                                "view" : "1"
                             },
                             {
                                "sequence_number" : "10",
                                "view" : "1",
                                "conditional_name" : "volunteerlevel",
                                "edit" : "0",
                                "conditional_value" : "Hotel",
                                "name" : "volunteerhotelpref",
                                "conditional" : "1",
                                "type" : "select",
                                "options" : "Male\nFemale\nAny",
                                "label" : "Hotel Rooming Preference",
                                "required" : "0"
                             },
                             {
                                "view" : "1",
                                "sequence_number" : "5",
                                "required" : "1",
                                "label" : "What role are you interested in?  Admin roles are as follows: Runners work with the Admins assigned to the slot, they will help GMs with getting their badges and perform health checks.  Admins will help seat players at tables and check DMs in.  Head admin will be the escalation point for any issues that arise.",
                                "options" : "DM - Adventurers League Only\nDM - Acquisitions Incorporated Only\nDM - Any\nAdmin\nAny",
                                "conditional" : "0",
                                "type" : "select",
                                "name" : "volunteerrole",
                                "edit" : "0"
                             }
                         ]
                        }
    convention_response = requests.put(convention_url, data= convention_params)
    convention_json = convention_response.json()
    print (convention_json)
    return()

# -----------------------------------------------------------------------
# Pull Convention Data from the database
# -----------------------------------------------------------------------
def list_convention_info(tteconvention_id):
    convention = Conventions()
    convention = Conventions.query.filter_by(tteid = tteconvention_id).first()
    convention_data = {}
    try:
        if convention.slots is not None:
            con_slots = json.loads(convention.slots)
            for slot in con_slots:
                try:
                    new_slot = int(slot)
                    convention_data[new_slot] = con_slots[slot]
                except ValueError:
                    pass
        if convention.tables is not None:
            convention_data['tables'] = convention.tables
    except:
        convention_data = None
        pass
    return(convention_data)

# -----------------------------------------------------------------------
# Pull Slots Data from the TTE API for the whole convention
# -----------------------------------------------------------------------
def tte_convention_slots_api_get(ttesession,tteconvention_id):
    slots_start = 1
    slots_total = 1000
    all_slots = list()
    slots_url = tteconvention_data['result']['_relationships']['slots']
    while slots_total >= slots_start:
        slots_params = {'session_id': ttesession['id'], '_page_number': slots_start}
        slots_response = requests.get('https://tabletop.events' + slots_url, params= slots_params)
        slots_json = slots_response.json()
        convention_slots = slots_json['result']['items']
        slots_total = int(slots_json['result']['paging']['total_pages'])
        for slots in convention_slots:
            all_slots.append(slots)
        if slots_start < slots_total:
            slots_start = int(slots_data['result']['paging']['next_page_number'])
        elif slots_start == slots_total:
            break
    return(all_slots)

# -----------------------------------------------------------------------
# Pull Slots Data from the TTE API for a specific event
# -----------------------------------------------------------------------
def tte_event_slots_api_get(ttesession,tteconvention_id,slots_url):
    slots_start = 1
    slots_total = 1000
    all_slots = list()
    while slots_total >= slots_start:
        slots_params = {'session_id': ttesession['id'], '_page_number': slots_start}
        slots_response = requests.get(slots_url, params= slots_params)
        slots_json = slots_response.json()
        convention_slots = slots_json['result']['items']
        slots_total = int(slots_json['result']['paging']['total_pages'])
        for slots in convention_slots:
            all_slots.append(slots)
        if slots_start < slots_total:
            slots_start = int(slots_json['result']['paging']['next_page_number'])
        elif slots_start == slots_total:
            break
    return(all_slots)

# -----------------------------------------------------------------------
# Create a list of tables assigned to the slot
# -----------------------------------------------------------------------
def slots_parse(event_slots):
    table_l= []
    slot_tables = []
    for slot in event_slots:
        table_l = slot['name'].split()
        table_str = table_l[0] + ' ' + table_l[1]
        if table_str not in slot_tables:
            slot_tables.append(table_str)
    return (slot_tables)

# -----------------------------------------------------------------------
# Save the event data to CSV
# -----------------------------------------------------------------------
def event_data_csv(events):
    folder = config.UPLOAD_FOLDER
    saveloc = folder + '/eventdata.csv'
    with open(saveloc, mode='w') as csv_file:
        fieldnames = ['event_number', 'name', 'startdaypart_name', 'duration', 'event_tables', 'host_count']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames,extrasaction='ignore')

        writer.writeheader()
        for event in events:
            writer.writerow(event)
# -----------------------------------------------------------------------
# Pull Hosts Data from the TTE API for a specific event
# -----------------------------------------------------------------------
def tte_event_hosts_api_get(ttesession,tteconvention_id,hosts_url):
    hosts_start = 1
    hosts_total = 1000
    all_hosts = list()
    while hosts_total >= hosts_start:
        hosts_params = {'session_id': ttesession['id'], '_page_number': hosts_start}
        hosts_response = requests.get('https://tabletop.events' + hosts_url, params= hosts_params)
        hosts_json = hosts_response.json()
        convention_hosts = hosts_json['result']['items']
        hosts_total = int(hosts_json['result']['paging']['total_pages'])
        for hosts in convention_hosts:
            all_hosts.append(hosts)
        if hosts_start < hosts_total:
            hosts_start = int(hosts_json['result']['paging']['next_page_number'])
        elif hosts_start == hosts_total:
            break
    return(all_hosts)

# -----------------------------------------------------------------------
# Get the Geolocation data (for the time zone of the con)
# -----------------------------------------------------------------------
def tte_convention_geolocation_api_get(ttesession,tteconvention_id):
  geolocation_params = {'session_id': ttesession['id'], '_include_related_objects': 'geolocation'}
  geolocation_response = requests.get(config.tte_url + "/convention/" + tteconvention_id, params= geolocation_params)
  geolocation_data = geolocation_response.json()
  geolocation_timezone = geolocation_data['result']['geolocation']['timezone']
  return(geolocation_timezone)

# -----------------------------------------------------------------------
# Parse a File for a convention
# -----------------------------------------------------------------------
def convention_parse(filename,tteconvention_id,tteconvention_name):
    #print('convention_parse')
    # Definitions
    slot = {}
    newheader = []
    convention_slots = []
    convention_tables = []
    convention = {}

    # Open CSV file and verify headers
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for header in reader.fieldnames:
            if 'Slot' in header:
                header_l = header.rsplit()
                newheader.append('slot ' + header_l[1])
            if 'Length' in header:
                newheader.append('length')
            if 'Table Start' in header:
                newheader.append('table_start')
            if 'Table End' in header:
                newheader.append('table_end')
            if 'Table Type' in header:
                newheader.append('table_type')
        reader.fieldnames = newheader
        for room_info in reader:
            tables = {}
            new_slot = {}
            for field in room_info:
                # Create the dict of slot time and length of each slot if the field is a slot field
                if 'slot' in field and room_info[field] is not 'X':
                    slot_num = field.rsplit()
                    new_slot = {'slot': slot_num[1] , 'time': room_info[field], 'length': room_info['length']}
                    # Add to a list of all the slots for the convention
                    convention_slots.append(new_slot)
            # Create a dict for each room of the convention
            tables = {'table_type': room_info['table_type'], 'table_start': room_info['table_start'],'table_end': room_info['table_end']}
            # Add the tables dict to a list of rooms
            convention_tables.append(tables)
        convention['slots'] = convention_slots
        convention['tables'] = convention_tables
        # save_convention(convention,tteconvention_id,tteconvention_name)
        return(convention)

# -----------------------------------------------------------------------
# Save a convention to the database
# -----------------------------------------------------------------------
def save_convention(convention,tteconvention_id,tteconvention_name):
    convention_exist = list_convention_info(tteconvention_id)
    new_convention = Conventions()
    #Check to see if the convention already exists
    #If the convention doesn't, Setup new convention database entry
    if convention_exist is None:
        new_convention.tteid = tteconvention_id
        new_convention.name = tteconvention_name
        new_convention.tables = convention['tables']
        new_convention.slots = convention['slots']
        db.session.merge(new_convention)
    else:
        saved = 'exists'
    try:
        db.session.commit()
        saved = 'saved'
        return (saved)
    except:
        logger.exception("Cannot save new convention")
        db.session.rollback()
        saved = 'failed'
        return (saved)

# -----------------------------------------------------------------------
# Get Convention Volunteer Information
# -----------------------------------------------------------------------
def tte_convention_volunteer_api_get(ttesession,tteconvention_id):
    volunteer_start = 1
    volunteer_total = 1000
    all_volunteers = list()
    ttevolunteer_url = 'https://tabletop.events' + tteconvention_data['result']['_relationships']['volunteers']
    while volunteer_total >= volunteer_start:
        volunteer_params = {'session_id': ttesession, 'convention_id': tteconvention_id, '_page_number': volunteer_start}
        volunteer_response = requests.get(ttevolunteer_url, params= volunteer_params)
        volunteer_json = volunteer_response.json()
        volunteer_data = volunteer_json['result']['items']
        volunteer_total = int(volunteer_json['result']['paging']['total_pages'])
        volunteer_start = int(volunteer_json['result']['paging']['page_number'])
        for volunteer in volunteer_data:
            all_volunteers.append(volunteer)
        if volunteer_start < volunteer_total:
            volunteer_start = int(volunteer_json['result']['paging']['next_page_number'])
        elif volunteer_start == volunteer_total:
            break
        else:
            break
    return(all_volunteers)

# -----------------------------------------------------------------------
# Get days of the convention
# -----------------------------------------------------------------------
def tte_convention_days_api_get(ttesession,tteconvention_id):
    #Declarations
    day_info = []
    # Get the data on the convention
    tteconvention_days_url = 'https://tabletop.events' + tteconvention_data['result']['_relationships']['days']
    # Use the day url to get data on the days
    day_params = {'session_id': ttesession, 'convention_id': tteconvention_id}
    day_response = requests.get(tteconvention_days_url, params= day_params)
    day_data = day_response.json()
    # Create a datetime value for each day, add to a new dict
    for item in day_data['result']['items']:
         dt = datetime.datetime.strptime(item['start_date'], '%Y-%m-%d %H:%M:%S')
         et = datetime.datetime.strptime(item['end_date'], '%Y-%m-%d %H:%M:%S')
         day_info.append({'id' : item['id'], 'day_time' : dt, 'end_time': et})
    return(day_info)

# -----------------------------------------------------------------------
# Post the Convention Days
# -----------------------------------------------------------------------
def tte_convention_days_api_post(ttesession,tteconvention_id,new_convention):
    # Declarations
    all_days = []
    all_dates = new_convention['dates'].split('\r\n')
    tteconvention_days_url = 'https://tabletop.events/api/conventionday'
    for date in all_dates:
        start_date = date + ' 12:00 AM'
        start_day = datetime.datetime.strptime(start_date, "%m/%d/%Y %I:%M %p")
        day_name = start_day.strftime('%a %b %m')
        end_day = start_day + datetime.timedelta(days=1)
        day_params = {
            'attendee_start_date': start_day,
            'attendee_end_date': end_day,
            'start_date': start_day,
            'end_date': end_day,
            'convention_id': tteconvention_id,
            'name': day_name
        }
        day_response = requests.post(tteconvention_days_url, params= day_params)
        day_json = day_response.json()
        print (day_json)
        current_day = day_json['id'],day_json['name']
        all_days.append(day_data)
    print (all_days)
    return()

# -----------------------------------------------------------------------
# Get the id for day parts
# -----------------------------------------------------------------------
def tte_convention_dayparts_api_get(ttesession,tteconvention_id):
    day_parts_start = 1
    day_parts_total = 1000
    all_dayparts = list()
    dayparts_url = tteconvention_data['result']['_relationships']['dayparts']

    while day_parts_total >= day_parts_start:
        dayparts_params = {'session_id': ttesession['id'], '_page_number': day_parts_start}
        dayparts_response = requests.get('https://tabletop.events' + dayparts_url, params= dayparts_params)
        dayparts_data = dayparts_response.json()
        convention_dayparts = dayparts_data['result']['items']
        day_parts_total = int(dayparts_data['result']['paging']['total_pages'])
        for dayparts in convention_dayparts:
            dayparts['datetime'] = datetime.datetime.strptime(dayparts['start_date'],'%Y-%m-%d %H:%M:%S')
            all_dayparts.append(dayparts)
        if day_parts_start < day_parts_total:
            day_parts_start = int(dayparts_data['result']['paging']['next_page_number'])
        elif day_parts_start == day_parts_total:
            break
    return(all_dayparts)

# -----------------------------------------------------------------------
# Delete all dayparts from TTE
# -----------------------------------------------------------------------
def tte_convention_dayparts_api_delete(ttesession,tteconvention_id,all_dayparts):
    for daypart in all_dayparts:
        daypart_delete_params = {'session_id': ttesession['id']}
        daypart_delete_url = 'https://tabletop.events/api/daypart/' + daypart['id']
        daypart_delete_response = requests.delete(daypart_delete_url, params= daypart_delete_params)
        daypart_delete_data = daypart_delete_response.json()
    return()

# -----------------------------------------------------------------------
# Volunteer Functions
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# Ingest Volunteers
# -----------------------------------------------------------------------
def volunteer_parse(filename,tteconvention_id):
    # Definitions
    newheader = []

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
            saved = volunteer_save(vol,tteconvention_id)
        return(saved)

# -----------------------------------------------------------------------
# Volunteer Save to Database
# -----------------------------------------------------------------------
def volunteer_save(new_volunteer,tteconvention_id):
    #Declarations
    tiers = []
    all_slots = []
    tteconventions = []
    cons = {}
    volunteer = Volunteers()
    old_volunteer = Volunteers()
    ttesession = session.get('ttesession')
    #Load the volunteers from the TRI database for this convention
    all_volunteers = list_volunteers(tteconvention_id)
    # Check the database to see if the volunteer already exists
    k = 'email', new_volunteer['email']
#    if k not in all_volunteers and new_volunteer['email'] != all_volunteers[k]:
    if k not in all_volunteers:
        volunteer.name = new_volunteer['name']
        volunteer.email = new_volunteer['email']
        volunteer.role = new_volunteer['role']
        if 'Tier 1' in new_volunteer['tiers']:
            tiers.append('1')
        if 'Tier 2' in new_volunteer['tiers']:
            tiers.append('2')
        if 'Tier 3' in new_volunteer['tiers']:
            tiers.append('3')
        if 'Tier 4' in new_volunteer['tiers']:
            tiers.append('4')
        if tiers is not None:
            volunteer.tiers = ','.join(tiers)
        if new_volunteer['hours'] == 'Badge':
            volunteer.hours = 10
        elif new_volunteer['hours'] == 'Hotel':
            volunteer.hours = 20
        else:
            try:
                volunteer.hours = int(new_volunteer['hours'])
            except TypeError:
                pass
            except ValueError:
                print (new_volunteer['email'], ' failed to parse hours')
        for field in new_volunteer:
            if 'slot' in field:
                slot_number = field.rsplit()
                slot_number = slot_number[1]
                if 'X' in new_volunteer[field]:
                    slot_id = None
                    slot_d = {}
                    slot_d[slot_number] = slot_id
                    con_slots.append(slot_d)
            cons[tteconvention_id] = con_slots
        volunteer.slots = cons
        tteconventions.append(tteconvention_id)
        volunteer.conventions = ','.join(tteconventions)
        ttevolunteer_id = tte_user_api_pull(ttesession,new_volunteer['email'])
        if ttevolunteer_id is None:
            try:
                volunteer.tteid = tte_user_add(ttesession,new_volunteer['email'],new_volunteer['name'],tteconvention_id)
                print ('Added new volunteer to TTE: ', new_volunteer['email'],new_volunteer['name'], volunteer.tteid)
                db.session.merge(volunteer)
            except:
                logger.exception("Cannot save volunteer")
                db.session.rollback()
                saved = 'failed'
                return (saved)
        else:
            volunteer.tteid = ttevolunteer_id
    # If the volunteer exists in the TRI User Database already but, add the new tteconvention to their conventions list
    #elif k in all_volunteers and tteconvention_id not in all_volunteers[k].tteconventions:
    #    old_volunteer = all_volunteers[k]
    #    tteconventions = old_volunteer.tteconventions
    #    tteconventions.append(tteconvention_id)
    #    old_volunteer.conventions = ','.join(tteconventions)
    #    ttevolunteer_id = tte_user_api_pull(ttesession,old_volunteer.email)
    #    if ttevolunteer_id is None:
    #        try:
    #            old_volunteer.tteid = tte_user_add(ttesession,old_volunteer.email,old_volunteer.name,tteconvention_id)
    #            print ('Added old volunteer to TTE: ', old_volunteer['email'],old_volunteer['name'], old_volunteer.tteid)
    #            db.session.merge(old_volunteer)
    #        except:
    #            logger.exception("Cannot save volunteer: ", old_volunteer['email'],old_volunteer['name'])
    #            db.session.rollback()
    #            saved = 'failed'
    #            return (saved)
    #    else:
    #        old_volunteer.tteid = ttevolunteer_id
    try:
        db.session.commit()
        saved = 'saved'
        return (saved)
    except:
        logger.exception("Cannot save volunteer")
        db.session.rollback()
        saved = 'failed'
        return (saved)

# -----------------------------------------------------------------------
# List all volunteers in database
# -----------------------------------------------------------------------
def list_volunteers(tteconvention_id):
    volunteer = Volunteers()
    db_volunteers = Volunteers.query.filter(Volunteers.conventions.ilike(tteconvention_id))
    all_volunteers = []
    v = {}
    for vol in db_volunteers:
        v['name'] = vol.name
        v['role'] = vol.role
        v['hours'] = vol.hours
        v['tiers'] = vol.tiers
        v['slots'] = vol.slots
        all_volunteers.append(v)
    return(all_volunteers)

# -----------------------------------------------------------------------
# Query if user exists in TTE
# -----------------------------------------------------------------------
def tte_user_api_pull(ttesession,volunteer_email):
    print ('tte_user_api_pull')
    volunteer_params = {'session_id': ttesession['id']}
    volunteer_url = 'https://tabletop.events' + '/api/user' + '?query=' + volunteer_email
    volunteer_response = requests.get(volunteer_url, params= volunteer_params)
    volunteer_json = volunteer_response.json()
    try:
        for vol in volunteer_json['result']['items']:
            volunteer_id = vol['id']
            print (vol['real_name'],vol['id'])
    except:
        print ('Unable to find: ', volunteer_email)
        volunteer_id = None
    return(volunteer_id)

# -----------------------------------------------------------------------
# Add user to TTE
# -----------------------------------------------------------------------
def tte_user_add(ttesession,volunteer_email,volunteer_name,tteconvention_id):
    #  print ('tte_user_add')
    volunteer_full_name = volunteer_name.rsplit()
    volunteer_first = volunteer_full_name[0]
    volunteer_last = volunteer_full_name[1]
    useradd_params = {'session_id': ttesession['id'],'convention_id' : tteconvention_id,'email_address' : volunteer_email,'firstname' : volunteer_first,'lastname' : volunteer_last,'phone_number' : '555-555-5555'}
    volunteer_response = requests.post('https://tabletop.events/api/volunteer/by-organizer', params= useradd_params)
    volunteer_data = volunteer_response.json()
    try:
        volunteer_id = volunteer_data['result']['id']
        return(volunteer_id)
    except:
        print ('Unable to add: ', volunteer_email)
        return()

# -----------------------------------------------------------------------
# Get Volunteer Shift Information
# -----------------------------------------------------------------------
def tte_volunteer_shifts_api_get(ttesession,tteconvention_id,user_id):
    volunteer_shifts_start = 1
    volunteer_shifts_total = 1000
    all_volunteer_shifts = list()
    ttevolunteer_shifts_url = 'https://tabletop.events/api/volunteershift' + user_id
    while volunteer_shifts_total >= volunteer_shifts_start:
        volunteer_shifts_params = {'session_id': ttesession, 'convention_id': tteconvention_id, '_page_number': volunteer_shifts_start}
        volunteer_shifts_response = requests.get(ttevolunteer_shifts_url, params= volunteer_shifts_params)
        volunteer_shifts_json = volunteer_shifts_response.json()
        volunteer_shifts_data = volunteer_shifts_data['result']['items']
        volunteer_shifts_total = int(volunteer_shifts_data['result']['paging']['total_pages'])
        volunteer_shifts_start = int(volunteer_shifts_data['result']['paging']['page_number'])
        for volunteer_shift in volunteer_shifts_data:
            volunteer_shift['shift_data'] = tte_shift_api_get(ttesession,tteconvention_id,volunteer_shift['shift_id'])
            all_volunteer_shifts.append(volunteer_shift)
        if volunteer_shifts_start < volunteer_shifts_total:
            volunteer_shifts_start = int(volunteer_shifts_data['result']['paging']['next_page_number'])
        elif volunteer_shifts_start == volunteer_shifts_total:
            break
        else:
            break
    return(all_volunteer_shifts)

# -----------------------------------------------------------------------
# Get Shift Information
# -----------------------------------------------------------------------
def tte_shift_api_get(ttesession,tteconvention_id,shift_id):
    shift_start = 1
    shift_total = 1000
    all_shift = list()
    tteshift_url = 'https://tabletop.events/api/shift' + shift_id
    shift_params = {'session_id': ttesession, 'convention_id': tteconvention_id, '_page_number': shift_start}
    shift_response = requests.get(tteshift_url, params= shift_params)
    shift_json = shift_response.json()
    shift_data = shift_data['result']['items']
    return(shift_data)

# -----------------------------------------------------------------------
# Slot Functions
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# Delete shofts from database
# -----------------------------------------------------------------------
def database_slot_delete(tteconvention_id):
    convention = Conventions()
    convention = Conventions.query.filter_by(tteid=tteconvention_id).first()
    convention.slots = None
    try:
        db.session.commit()
        deleted = 'Deleted all slots'
        return (deleted)
    except:
        logger.exception("Cannot delete slots")
        db.session.rollback()
        deleted = 'failed'
        return (deleted)

# -----------------------------------------------------------------------
# Post to TTE the Volunteer Shifts
# -----------------------------------------------------------------------
def tte_convention_volunteer_shift_api_post(ttesession,tteconvention_id,convention_info):
    print ('tte_convention_volunteer_shift_api_post')
    # Get the information on Convention Days
    day_info = tte_convention_days_api_get(ttesession,tteconvention_id)
    # Get the information on preexisting shifts
    shiftypes_info = tte_convention_volunteer_shifttypes_api_get(ttesession,tteconvention_id)
    # If there are any existing shifts, look for a match on the name
    if len(shiftypes_info) != 0:
        for shifttype in shiftypes_info:
            if 'Slot' in shifttype['name']:
                shifttype_name = shifttype['name']
                shifttype_id = shifttype['id']
                print ('Found shift type ', shifttype_name,shifttype_id)
            else:
                pass
    else:
        shifttype_name = 'Slot'
        shifttype_id = tte_convention_volunteer_shifttypes_api_post(ttesession,tteconvention_id,shifttype_name)
        print ('Created shift type ', shifttype_name,shifttype_id)
    # For each slot, get the information we need to be able to post the a volunteer shift
    for slot in convention_info['slots']:
        shift_name = 'Slot ' + slot['slot']
        slot_length = int(slot['length'])
        shift_actual = datetime.datetime.strptime(slot['time'], '%m/%d/%y %I:%M:%S %p')
        shift_start = datetime_utc_convert(ttesession,tteconvention_id,shift_actual)
        shift_end = shift_start + datetime.timedelta(hours=slot_length)
        for day in day_info:
            slot_date = datetime.date(shift_actual.year,shift_actual.month,shift_actual.day)
            shift_date = datetime.date(day['day_time'].year,day['day_time'].month,day['day_time'].day)
            print (slot_date,shift_date)
            # Compare the dates of the slot and the shift to get the tteid to use to post the shift
            if slot_date == shift_date:
                day_id = day['id']
                shift_params = {
                'session_id': ttesession['id'],
                'convention_id': tteconvention_id,
                'name': shift_name,
                'quantity_of_volunteers': '255',
                'start_time': shift_start,
                'end_time': shift_end,
                'conventionday_id': day_id,
                'shifttype_id': shifttype_id
                }
                shift_response = requests.post(config.tte_url + '/shift', params= shift_params)
                shift_json = shift_response.json()
                print (shift_json)
    return()

# -----------------------------------------------------------------------
# Pull shifts from TTE
# -----------------------------------------------------------------------
def tte_convention_volunteer_shifttypes_api_get(ttesession,tteconvention_id):
    shifttypes_url = 'https://tabletop.events' + tteconvention_data['result']['_relationships']['shifttypes']
    shifttypes_params = {'session_id': ttesession, 'convention_id': tteconvention_id}
    shifttypes_response = requests.get(shifttypes_url, params= shifttypes_params)
    shifttypes_json = shifttypes_response.json()
    shifttypes_data = shifttypes_json['result']['items']
    return (shifttypes_data)

# -----------------------------------------------------------------------
# Post shiftstypes to TTE
# -----------------------------------------------------------------------
def tte_convention_volunteer_shifttypes_api_post(ttesession,tteconvention_id,shifttype_name):
    shifttypes_params = {'session_id': ttesession['id'], 'convention_id': tteconvention_id, 'name': shifttype_name}
    shifttypes_response = requests.post(config.tte_url + '/shifttype', params= shifttypes_params)
    shifttypes_json = shifttypes_response.json()
    shifttypes_id = shifttypes_json['result']['id']
    return(shifttypes_id)

# -----------------------------------------------------------------------
# Post slots to TTE as Day Parts
# -----------------------------------------------------------------------
def tte_convention_dayparts_api_post(ttesession,tteconvention_id,convention_info):
    #Declarations
    slots = {}
    # Get data on the days
    day_info = tte_convention_days_api_get(ttesession,tteconvention_id)
    # Loop through the day in 30 minute increments
    for day in day_info:
        day_id = day['id']
        day_start = day['day_time']
        day_end = day['end_time']
        daypart_time = day_start
        while daypart_time < day_end:
            convention_datetime = datetime_timezone_convert(ttesession,tteconvention_id,daypart_time)
            daypart_name = datetime.datetime.strftime(convention_datetime, '%a %I:%M %p')
            # API Post to TTE (Day Parts)
            daypart_params = {'session_id': ttesession['id'], 'convention_id': tteconvention_id, 'name': daypart_name, 'start_date': daypart_time, 'conventionday_id': day_id}
            daypart_response = requests.post(config.tte_url + '/daypart', params= daypart_params)
            daypart_data = daypart_response.json()
            daypart_time = daypart_time + datetime.timedelta(minutes= 30)
    return('saved')

# -----------------------------------------------------------------------
# Pull TTE Volunteer Shifts
# -----------------------------------------------------------------------
def tte_convention_volunteer_shifts_api_get(ttesession,tteconvention_id):
    shifts_start = 1
    shifts_total = 1000
    all_shifts = list()
    # Get the data on the convention
    tteconvention_shifts_url = 'https://tabletop.events' + tteconvention_data['result']['_relationships']['shifts']
    while shifts_total >= shifts_start:
        shifts_params = {'session_id': ttesession['id'], '_include_related_objects': 'shifttype'}
        shifts_response = requests.get(tteconvention_shifts_url, params= shifts_params)
        shifts_json = shifts_response.json()
        shifts_total = int(shifts_json['result']['paging']['total_pages'])
        shifts_data = shifts_json['result']['items']
        for shifts in shifts_data:
            all_shifts.append(shifts)
        if shifts_start < shifts_total:
            shifts_start = int(shifts_json['result']['paging']['next_page_number'])
        elif shifts_start == shifts_total:
            break
    return(all_shifts)

# -----------------------------------------------------------------------
# Delete all shifts from TTE
# -----------------------------------------------------------------------
def tte_convention_volunteer_shifts_api_delete(ttesession,tteconvention_id,all_shifts):
    for shift in all_shifts:
        shift_delete_params = {'session_id': ttesession['id']}
        shift_delete_url = 'https://tabletop.events/api/shift/' + shift['id']
        shift_delete_response = requests.delete(shift_delete_url, params= shift_delete_params)
        shift_delete_data = shift_delete_response.json()
    return()

# -----------------------------------------------------------------------
# Event Functions
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# Parse Events Matrix
# -----------------------------------------------------------------------
def event_parse(filename,tteconvention_id,tteconvention_name):
    #Definitions
    newheader = []
    savedevents = []
    # Open CSV file and verify headers
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for header in reader.fieldnames:
            if 'Event Name' in header:
                newheader.append('name')
#            elif 'Date' in header:
#                newheader.append('date_info')
#            elif 'Start Time' in header:
#                newheader.append('starttime')
            elif "Datetime" in header:
                newheader.append('datetime')
            elif 'Duration' in header:
                newheader.append('duration')
            elif 'Table Count' in header:
                newheader.append('tablecount')
            elif 'Hosts' in header:
                newheader.append('hosts')
            elif 'Type' in header:
                newheader.append('type')
            elif 'Tier' in header:
                newheader.append('tier')
        reader.fieldnames = newheader
        for event in reader:
            savedevents.append(event)
        return(savedevents)

# -----------------------------------------------------------------------
# Push Events to TTE
# -----------------------------------------------------------------------
def tte_convention_events_api_post(ttesession,tteconvention_id,savedevents):
    print ('tte_convention_events_api_post testing')
    all_events = []
    # For each event, gather the information needed to post the event
    # Get the convention days information
    convention_days = tte_convention_days_api_get(ttesession,tteconvention_id)
    # Get the dayparts for the convention
    convention_dayparts = tte_convention_dayparts_api_get(ttesession,tteconvention_id)
    for event in savedevents:
        event_type_l = []
        print (event)
        #Get the event types from TTE
        event_types = tte_convention_eventtypes_api_get(ttesession,tteconvention_id)
        # Compare the Name and Tier of the event types (if any exist) with the provided type listed for the event
        # If the event is a game, get a list of event types, checking if they have a tier or not.
        # If the event isn't a game, return the list of event types that don't have tiers.
        if event['tier'] != None:
            event_type_l = [type for type in event_types if type['name'] == event['type'] and event['tier'] in type['custom_fields']]
        else:
            event_type_l = [type for type in event_types if type['name'] == event['type']]
        # If there are event types and a match is found, assign the id of the match to the event
        if len(event_type_l) !=0:
            event['type_id'] = e['id']
        else:
            # If there isn't a match, create a new Event Type and return the TTE id for that Type
            if event['tier'] !='':
                print ('Adding Event Type to TTE: ', event['type'], event['tier'])
            else:
                print ('Adding Event Type to TTE: ', event['type'])
            event['type_id'] = tte_convention_events_type_api_post(ttesession,tteconvention_id,event)
        # Calculate the datetime value of the event
        event['duration'] = int(event['duration'])
        event['unconverted_datetime'] = datetime.datetime.strptime(event['datetime'],'%m/%d/%y %I:%M:%S %p')
        #Convert the datetime value to UTC
        event['datetime_utc'] = datetime_utc_convert(ttesession,tteconvention_id,event['unconverted_datetime'])
        # Identify the Day Id for the convention
        for day in convention_days:
            day['date_check'] = datetime.date(day['day_time'].year,day['day_time'].month,day['day_time'].day)
            event['date_check'] = datetime.date(event['datetime_utc'].year,event['datetime_utc'].month,event['datetime_utc'].day)
            if event['date_check'] == day['date_check']:
                event['day_id'] = day['id']
        # Get the slots for the convention
        conventions_slots = tte_convention_slots_api_get(ttesession,tteconvention_id)
        # Define a list to be filled with the slot times used (in increments of 30 minutes) in the event
        all_slot_times = []
        # Define a list to be filled with the slot info (id and datetime) of the event
        slot_list = []
        for x in range(event['duration'],30):
            slot_time = event['datetime_utc'] + datetime.timedelta(minutes=x)
            all_slot_times.append(slot_time)
        # Parse through the convention dayparts to find the
        # Then compare to see if they are equal to determine the TTE ID of the time
        # Parse through the datetimes of the day and the slottimes of the event
        for dayparts in convention_dayparts:
            for slot_time in all_slot_times:
                # Find the id of the daypart for the start of the event
                # Add to the list of slot times and ids
                if dayparts['datetime'] == slot_time and event['datetime_utc'] == dayparts['datetime']:
                    slot_info.append(dayparts['id'], dayparts['datetime'])
                    event['dayparts_start_id'] = dayparts['id']
                # Add other ids of correspdonging slot times that fall within the event
                elif dayparts['datetime'] == slot_time and event['datetime_utc'] != dayparts['datetime']:
                        slot_info.append(dayparts['id'], dayparts['datetime'])
        # Verify an events has a ID for the day, ID for the Event Type, and ID for the Day Part
        if event['day_id'] and event['type_id'] and event['dayparts_id']:
            # Create the Event
            event_params = {'session_id': ttesession['id'], 'convention_id': tteconvention_id, 'name' : event['name'], 'max_tickets' : 6, 'priority' : 3, 'age_range': 'all', 'type_id' : event['type_id'], 'conventionday_id': event['day_id'], 'duration' : event['duration'], 'alternatedaypart_id' : event['dayparts_start_id'], 'preferreddaypart_id' : event['dayparts_start_id']}
            event_response = requests.post('https://tabletop.events/api/event', params= event_params)
            event_json = event_response.json()
            event_data = event_data['result']
            print ('Added new Event to TTE: ', event_data['name'], event_data['unconverted_datetime'], event_data['id'])
            event['id'] = event_data['id']
            # Add slots for the event (assigns tables and times)
            for i in range(1,event['tablecount'],1):
                for conslot in conventions_slots:
                    if conslot['room_id'] == event_data['room_id']:
                        for eventslot in slot_info:
                            if eventslot['id'] == conslot['daypart_id'] and conslot['is_assigned'] == 0:
                                event_slot_url = 'https://tabletop.events/api/slot/' + conslot['id']
                                event_slot_params = {'session_id': ttesession['id'], 'event_id': event['id']}
                                event_slot_response = requests.put(event_slot_url, params=event_slot_params)
                                event_slot_json = event_slot_response.json()
                                if event_slot_json['id']:
                                    event_slot_l.append(event_slot_json['id'])
                                    event['slots'] = event_slot_l
                                    print ('Added event to slot ', event_slot_json['name'])
                                else:
                                    print ('Unable to add slot', eventslot)
                            else:
                                print ('Unable to add slot ', eventslot)
                    else:
                        print ('No matching room found for event')
            all_events.append(event)
    return(all_events)

# -----------------------------------------------------------------------
# Get Event Types Information
# -----------------------------------------------------------------------
def tte_convention_eventtypes_api_get(ttesession,tteconvention_id):
      eventtypes_start = 1
      eventtypes_total = 1000
      all_eventtypes = list()
      # Get the data on the convention
      tteconvention_eventtypes_url = 'https://tabletop.events' + tteconvention_data['result']['_relationships']['eventtypes']
      # Loop through the eventtypes for the convention
      while eventtypes_total >= eventtypes_start:
        eventtypes_params = {'session_id': ttesession, 'convention_id': tteconvention_id}
        eventtypes_response = requests.get(tteconvention_eventtypes_url, params= eventtypes_params)
        eventtypes_json = eventtypes_response.json()
        eventtypes_data = eventtypes_json['result']['items']
        eventtypes_total = int(eventtypes_json['result']['paging']['total_pages'])
        for eventtypes in eventtypes_data:
            eventtypes_d = dict()
            eventtypes_d['id'] = eventtypes['id']
            eventtypes_d['name'] = eventtypes['name']
            all_eventtypes.append(eventtypes_d)
        if eventtypes_start < eventtypes_total:
            eventtypes_start = int(eventtypes_json['result']['paging']['next_page_number'])
        elif eventtypes_start == eventtypes_total:
            break
      return(all_eventtypes)

# -----------------------------------------------------------------------
# Post a new Event Type
# -----------------------------------------------------------------------
def tte_convention_events_type_api_post(ttesession,tteconvention_id,event_type):
    #print ('tte_convention_events_type_api_post')
    if event_type['tier'] != None:
        custom_tier = {'required': 1, 'type': 'text', 'label': 'Tier', 'name': 'tier', 'conditional': 0, 'edit': 0, 'view': 1}
        events_type_params = {'session_id': ttesession['id'], 'convention_id': tteconvention_id, 'name': event_type['type'], 'limit_volunteers': 0, 'max_tickets': 6, 'user_submittable': 0, 'default_cost_per_slot': 0, 'limit_ticket_availability': 0, 'custom_fields': custom_tier}
    else:
        events_type_params = {'session_id': ttesession['id'], 'convention_id': tteconvention_id, 'name': event_type['type'], 'limit_volunteers': 0, 'max_tickets': 6, 'user_submittable': 0, 'default_cost_per_slot': 0, 'limit_ticket_availability': 0}
    events_type_response = requests.post(config.tte_url + '/eventtype', params= events_type_params)
    events_type_json = events_type_response.json()
    events_type_id = events_type_json['result']['id']
    return(events_type_id)

# -----------------------------------------------------------------------
# Add host to an event
# -----------------------------------------------------------------------
def tte_event_host_post(ttesession,event_id,host_id):
  host_params = {'session_id': ttesession['id'] }
  host_url = 'https://tabletop.events/api/event/' + event_id + '/host/' + host_id
  host_response = requests.post(host_url, params= host_params)
  host_json = host_response.json()
  host_data = host_json['result']
  return(host_data)

# -----------------------------------------------------------------------
# Get User Events Information
# -----------------------------------------------------------------------
def tte_user_events_api_get(ttesession,user_id):
    user_events_start = 1
    user_events_total = 1000
    all_user_events = list()
    tteuser_events_url = 'https://tabletop.events/api/'
    while user_events_total >= user_events_start:
        user_events_params = {'session_id': ttesession, 'convention_id': tteconvention_id, '_page_number': user_events_start}
        user_events_response = requests.get(tteuser_events_url, params= user_events_params)
        user_events_json = user_events_response.json()
        user_events_data = user_events_data['result']['items']
        user_events_total = int(user_events_data['result']['paging']['total_pages'])
        user_events_start = int(user_events_data['result']['paging']['page_number'])
        for user_events in user_events_data:
            all_user_events.append(daypart)
        if user_events_start < user_events_total:
            user_events_start = int(user_events_data['result']['paging']['next_page_number'])
        elif user_events_start == user_events_total:
            break
        else:
            break
    return(all_user_events)

# -----------------------------------------------------------------------
# Get Event Dayparts Information
# -----------------------------------------------------------------------
def tte_eventdayparts_api_get(ttesession,tteconvention_id,event_id):
    eventdayparts_start = 1
    eventdayparts_total = 1000
    all_eventdayparts = list()
    tteeventdayparts_url = 'https://tabletop.events/api/event/' + event_id + '/dayparts'
    while eventdayparts_total >= eventdayparts_start:
        eventdayparts_params = {'session_id': ttesession, 'convention_id': tteconvention_id, '_page_number': eventdayparts_start, '_include_relationships': 1}
        eventdayparts_response = requests.get(tteeventdayparts_url, params= eventdayparts_params)
        eventdayparts_json = eventdayparts_response.json()
        eventdayparts_data = eventdayparts_data['result']['items']
        eventdayparts_total = int(eventdayparts_data['result']['paging']['total_pages'])
        eventdayparts_start = int(eventdayparts_data['result']['paging']['page_number'])
        for daypart in eventdayparts_data:
            all_event.append(daypart)
        if eventdayparts_start < eventdayparts_total:
            eventdayparts_start = int(eventdayparts_data['result']['paging']['next_page_number'])
        elif eventdayparts_start == eventdayparts_total:
            break
        else:
            break
    return(all_eventdayparts)

# -----------------------------------------------------------------------
# Get Event Information
# -----------------------------------------------------------------------
def tte_event_api_get(ttesession,tteconvention_id,event_id):
    event_start = 1
    event_total = 1000
    all_event = list()
    tteeevnt_url = 'https://tabletop.events/api/event/' + event_id
    while event_total >= event_start:
        event_params = {'session_id': ttesession, 'convention_id': tteconvention_id, '_page_number': event_start, '_include_relationships': 1}
        event_response = requests.get(tteeevnt_url, params= event_params)
        event_data = event_response.json()
        convention_event = event_data['result']['items']
        event_total = int(event_data['result']['paging']['total_pages'])
        event_start = int(event_data['result']['paging']['page_number'])
        for event in convention_event:
            all_event.append(event)
        if event_start < event_total:
            event_start = int(event_data['result']['paging']['next_page_number'])
        elif event_start == event_total:
            break
        else:
            break
    return(all_event)

# -----------------------------------------------------------------------
# Delete all Events for the Convention
# -----------------------------------------------------------------------
def tte_convention_events_api_delete(ttesession,tteconvention_id,allevents):
    for event in allevents:
        event_delete_params = {'session_id': ttesession['id']}
        event_delete_url = 'https://tabletop.events/api/event/' + event['id']
        event_delete_response = requests.delete(event_delete_url, params= event_delete_params)
        event_delete_data = event_delete_response.json()
    return()

# -----------------------------------------------------------------------
# Rooms and Spaces (Tables) Functions
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# Post Tables and Rooms to Convention
# -----------------------------------------------------------------------
def tte_convention_roomnsandspaces_api_post(ttesession,tteconvention_id,convention_info):
    print ('tte_convention_roomnsandspaces_api_post:')
    all_spaces = []
    spaces_data = {}
    for room in convention_info['tables']:
        rooms_params = {'session_id': ttesession['id'], 'convention_id': tteconvention_id, 'name': room['table_type'] }
        rooms_response = requests.post(config.tte_url + '/room', params= rooms_params)
        rooms_json = rooms_response.json()
        room_id = rooms_json['result']['id']
        room_name = rooms_json['result']['name']
        for table_num in range(int(room['table_start']),int(room['table_end'])):
            table_name = 'Table ' + str(table_num) + " " + room['table_type']
            spaces_params = {'session_id': ttesession['id'], 'convention_id': tteconvention_id, 'room_id': room_id, 'name': table_name, 'max_tickets': 6}
            spaces_response = requests.post(config.tte_url + '/space', params= spaces_params)
            spaces_json = spaces_response.json()
            space_id = spaces_json['result']['id']
            space_name = spaces_json['result']['name']
            spaces_data = {'space_id': space_id,'space_name': space_name, 'table_type': room_name,'room_id': room_id}
            all_spaces.append(spaces_data)
    return(all_spaces)

# -----------------------------------------------------------------------
# Delete Tables and Rooms in Convention
# -----------------------------------------------------------------------
def tte_convention_roomnsandspaces_api_delete(ttesession,tteconvention_id,tterooms,ttespace):
    # print ('tte_convention_roomnsandspaces_api_delete:')
    for space in ttespace:
        space_delete_params = {'session_id': ttesession['id']}
        space_delete_url = 'https://tabletop.events/api/space/' + space['id']
        space_delete_response = requests.delete(space_delete_url, params= space_delete_params)
        space_delete_data = space_delete_response.json()
    for room in tterooms:
        room_delete_params = {'session_id': ttesession['id']}
        room_delete_url = 'https://tabletop.events/api/room/' + room['id']
        room_delete_response = requests.delete(room_delete_url, params= room_delete_params)
        room_delete_data = room_delete_response.json()
    return()

# -----------------------------------------------------------------------
# Get Table Information
# -----------------------------------------------------------------------
def tte_convention_spaces_api_get(ttesession,tteconvention_id):
    # print ('tte_convention_spaces_api_get:')
    spaces_start = 1
    spaces_total = 1000
    all_spaces = list()
    tteconvention_spaces_url = 'https://tabletop.events' + tteconvention_data['result']['_relationships']['spaces']
    # Loop through the spaces for the convention
    while spaces_total >= spaces_start:
        spaces_params = {'session_id': ttesession, 'convention_id': tteconvention_id, '_page_number': spaces_start}
        spaces_response = requests.get(tteconvention_spaces_url, params= spaces_params)
        spaces_data = spaces_response.json()
        convention_spaces = spaces_data['result']['items']
        spaces_total = int(spaces_data['result']['paging']['total_pages'])
        spaces_start = int(spaces_data['result']['paging']['page_number'])
        for spaces in convention_spaces:
            all_spaces.append(spaces)
        if spaces_start < spaces_total:
            spaces_start = int(spaces_data['result']['paging']['next_page_number'])
        elif spaces_start == spaces_total:
            break
        else:
            break
    return(all_spaces)

# -----------------------------------------------------------------------
# Get Room Information
# -----------------------------------------------------------------------
def tte_convention_rooms_api_get(ttesession,tteconvention_id):
      rooms_start = 1
      rooms_total = 1000
      all_rooms = list()
      tteconvention_rooms_url = 'https://tabletop.events' + tteconvention_data['result']['_relationships']['rooms']
      # Loop through the rooms for the convention
      while rooms_total >= rooms_start:
        rooms_params = {'session_id': ttesession, 'convention_id': tteconvention_id, '_page_number': rooms_start}
        rooms_response = requests.get(tteconvention_rooms_url, params= rooms_params)
        rooms_data = rooms_response.json()
        convention_rooms = rooms_data['result']['items']
        rooms_total = int(rooms_data['result']['paging']['total_pages'])
        rooms_start = int(rooms_data['result']['paging']['page_number'])
        for rooms in convention_rooms:
            all_rooms.append(rooms)
        if rooms_start < rooms_total:
            rooms_start = int(rooms_data['result']['paging']['next_page_number'])
        elif rooms_start == rooms_total and rooms_total:
            break
        else:
          break
      return(all_rooms)

# -----------------------------------------------------------------------
# Get all events for Convention
# -----------------------------------------------------------------------
def tte_events_api_get(ttesession,tteconvention_id):
    events_start = 1
    events_total = 1000
    all_events = list()
    while events_total >= events_start:
        events_url = tteconvention_data['result']['_relationships']['events']
        events_params = {'session_id': ttesession['id'], 'tteconvention_id': tteconvention_id, '_page_number': events_start, '_include_relationships':1}
        events_response = requests.get('https://tabletop.events' + events_url,params= events_params)
        events_data = events_response.json()
        convention_events = events_data['result']['items']
        events_total = int(events_data['result']['paging']['total_pages'])
        for events in convention_events:
            all_events.append(events)
        if events_start < events_total:
            events_start = int(events_data['result']['paging']['next_page_number'])
        elif events_start == events_total:
            break
    return(all_events)

# -----------------------------------------------------------------------
# Geolocation Functions
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# Query for a location id
# -----------------------------------------------------------------------
def tte_geolocation_api_get(ttesession,convention_info):
    geolocation_name = convention_info['location']
    geolocation_url = 'https://tabletop.events/api/geolocation' + '?query=' + convention_info['location']
    geolocation_params = {'session_id': ttesession['id']}
    geolocation_response = requests.get(geolocation_url, params= geolocation_params)
    geolocation_json = geolocation_response.json()
    try:
        for location in geolocation_json['result']['items']:
            new_date = datetime.datetime.strptime(location['date_created'],'%Y-%m-%d %H:%M:%S')
            try:
                old_date
            except NameError:
                old_date = None
            if old_date is None:
                old_date = new_date
                geolocation_id = location['id']
            if new_date > old_date:
                old_date = new_date
                geolocation_id = location['id']
            else:
                geolocation_id = location['id']
                pass
    except:
        print ('Could not find location', convention_info, 'adding to TTE')
        geolocation_id = tte_geolocation_api_post(ttesession,convention_info)
    return(geolocation_id)

# -----------------------------------------------------------------------
# Create a new location
# -----------------------------------------------------------------------
def tte_geolocation_api_post(ttesession,new_convention):
    geolocation_url = '/api/geolocation'
    geolocation_params = {'session_id': ttesession['id'], 'name': new_convention['location']}
    geolocation_response = requests.post('https://tabletop.events' + geolocation_url, params= geolocation_params)
    geolocation_json = geolocation_response.json()
    geolocation_id = geolocation_json['result']['id']
    return(geolocation_id)

# -----------------------------------------------------------------------
# Get a location name from a tte ID
# -----------------------------------------------------------------------
def tte_geolocation_byid_api_get(ttesession):
    geolocation_url = '/api/geolocation/' + tteconvention_data['result']['geolocation_id']
    geolocation_params = {'session_id': ttesession['id']}
    geolocation_response = requests.get('https://tabletop.events' + geolocation_url, params= geolocation_params)
    geolocation_json = geolocation_response.json()
    geolociation_name = geolocation_json['result']['name']
    return(geolociation_name)

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
    logout = LogoutForm()
    # Check to see if the user already exists.
    # If it does, pass the user's name to the render_template
    if 'name' in session:
        name = session.get('name')
        ttesession = session.get('ttesession')
        if request.method == 'POST':
            if request.form.get('logoutsubmit'):
                session.pop('name')
                delete_session_params = {'session_id': ttesession['id']}
                delete_session = requests.delete('https://tabletop.events/api/session/' + ttesession['id'], params= delete_session_params)
                session.pop('ttesession')
                return render_template('base.html')
            else:
                pass
        else:
            return render_template('base.html', logout = logout, **{'name' : name})
    else:
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
# New Convention Route
# -----------------------------------------------------------------------
@app.route('/newconvention', methods=['GET', 'POST', 'PUT'])
def newconvention():
    # Declarations
    new_convention = {}
    # Call the global so we can modify it in the function with the API call.
    ttesession = session.get('ttesession')
    # Form Function calls
    newconventionform = NewConventionForm(request.form)
    if request.method == "POST":
        print (request.form)
        new_convention['name'] = request.form['name']
        new_convention['location'] = request.form['location']
        new_convention['description'] = request.form['description']
        new_convention['phone_number'] = request.form['phone_number']
        new_convention['email'] = request.form['email']
        new_convention['dates'] = request.form['dates']
        if newconventionform.validate():
            print ('Creating Convention')
            created_convention = tte_convention_convention_api_post(ttesession,new_convention)
            print ('Convention ', new_convention['name'], created_convention, ' created')
            return render_template('newconvention.html', newconventionform=newconventionform)
    return render_template('newconvention.html', newconventionform=newconventionform)

# -----------------------------------------------------------------------
# Conventions Route
# -----------------------------------------------------------------------
@app.route('/conventions', methods=['GET', 'POST', 'PUT'])
def conventions():
    # Declarations
    name = session.get('name')
    ttesession = session.get('ttesession')
    folder = config.UPLOAD_FOLDER
    files = os.listdir(folder)
    tteconventions = gettteconventions(ttesession)
    # Form Function calls
    conform = ConForm(request.form, obj=tteconventions)
    conform.selectcon.choices = [(tteconventions[con]['id'],tteconventions[con]['name']) for con in tteconventions]
    fileform = FileForm(request.form, obj=files)
    fileform.selectfile.choices = [(file,file) for file in files]
    if request.method == "POST":
        # Pull all the data regarding the convention
        if request.form.get('consubmit'):
            all_days = []
            session['tteconvention_id'] = request.form.get('selectcon',None)
            print ('Getting Convention Information')
            tte_convention_api_get(ttesession,session['tteconvention_id'])
            updateconform = conform_info()
            print (ttesession,session['tteconvention_id'])
            #event_data_csv(tteconvention_data['events'])
            return render_template('conventions.html', updateconform=updateconform, conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_data' : tteconvention_data,
            })
        if request.form.get('conventionsubmit') and session.get('tteconvention_id') is not None:
                update_convention = {}
                print ('Updating the convention')
                update_convention['name'] = request.form['name']
                update_convention['location'] = request.form['location']
                update_convention['description'] = request.form['description']
                update_convention['email'] = request.form['email']
                update_convention['phone_number'] = request.form['phone_number']
                update_convention['dates'] = request.form['dates']
                tte_convention_convention_tristandard_api_put(ttesession)
                tte_convention_convention_api_put(ttesession,update_convention)
                updateconform = conform_info()
                return render_template('conventions.html', updateconform=updateconform, conform=conform, fileform=fileform, **{'name' : name,
                'tteconventions' : tteconventions,
                'tteconvention_data' : tteconvention_data,
                })
        if request.form.get('volunteersave') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_name = tteconvention_data['result']['name']
            # Volunteer Management
            volunteerselect = request.form.get('selectfile')
            location = os.path.join(folder,volunteerselect)
            volunteers = volunteer_parse(location,tteconvention_id)
            savedvolunteers = list_volunteers(session['tteconvention_id'])
            updateconform = conform_info()
            return render_template('conventions.html', updateconform=updateconform, conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            'savedvolunteers' : savedvolunteers
            })
        if request.form.get('conventionsave') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_name = tteconvention_data['result']['name']
            # Slot Management
            conventionselect = request.form.get('selectfile')
            location = os.path.join(folder,conventionselect)
            print ('Parsing the Convention Matrix File')
            convention_info = convention_parse(location,tteconvention_id,tteconvention_name)
            print ('Creating the Volunteer Shifts')
            tte_convention_volunteer_shift_api_post(ttesession,tteconvention_id,convention_info)
            updateconform = conform_info()
            return render_template('conventions.html', updateconform=updateconform, conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            'convention_info' : convention_info,
            })
        if request.form.get('eventsave') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_name = tteconvention_data['result']['name']
            eventselect = request.form.get('selectfile')
            location = os.path.join(folder,eventselect)
            savedevents = event_parse(location,tteconvention_id,tteconvention_name)
            pushevents = tte_convention_events_api_post(ttesession,tteconvention_id,savedevents)
            updateconform = conform_info()
            return render_template('conventions.html', updateconform=updateconform, conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            'savedevents' : savedevents
            })
        if request.form.get('eventsdelete') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_name = tteconvention_data['result']['name']
            tteevents = tte_events_api_get(ttesession,tteconvention_id)
            deleteevents = tte_convention_events_api_delete(ttesession,tteconvention_id,tteevents)
            updateconform = conform_info()
            return render_template('conventions.html', updateconform=updateconform, conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            'savedevents' : savedevents
            })
        if request.form.get('shiftsdelete') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_name = tteconvention_data['result']['name']
            tteshifts = tte_convention_volunteer_shifts_api_get(ttesession,tteconvention_id)
            deleteshifts = tte_convention_volunteer_shifts_api_delete(ttesession,tteconvention_id,tteshifts)
            convention_info = list_convention_info(tteconvention_id)
            #databaseslotdelete = database_slot_delete(tteconvention_id)
            updateconform = conform_info()
            return render_template('conventions.html', updateconform=updateconform, conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            })
        if request.form.get('daypartsdelete') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_name = tteconvention_data['result']['name']
            ttedayparts = tte_convention_dayparts_api_get(ttesession,tteconvention_id)
            deletedayparts = tte_convention_dayparts_api_delete(ttesession,tteconvention_id,ttedayparts)
            updateconform = conform_info()
            return render_template('conventions.html', updateconform=updateconform, conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            })
        if request.form.get('roomsandtablesdelete') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_name = tteconvention_data['result']['name']
            tterooms = tte_convention_rooms_api_get(ttesession,tteconvention_id)
            ttespace = tte_convention_spaces_api_get(ttesession,tteconvention_id)
            tte_convention_roomnsandspaces_api_delete(ttesession,tteconvention_id,tterooms,ttespace)
            updateconform = conform_info()
            return render_template('conventions.html',  updateconform=updateconform, conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            })
        else:
            return render_template('conventions.html',  updateconform=updateconform, conform=conform, fileform=fileform, **{'name' : name })

    else:
        return render_template('conventions.html', conform=conform, fileform=fileform, **{'name' : name,
        })
# -----------------------------------------------------------------------
# Run Program
# -----------------------------------------------------------------------
if __name__ == '__main__':
    app.run(port=config.PORT, host=config.HOST)
