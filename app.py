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

# -----------------------------------------------------------------------
# Database models
# -----------------------------------------------------------------------
class Conventions(db.Model):
    name = db.Column(db.String(255))
    tteid = db.Column(db.String(255), primary_key=True)
    slots = db.Column(db.String(2048))
#    events = db.Column(db.String(2048))

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
    name = TextField('Name:', validators=[validators.DataRequired()])
    email = TextField('Email:', validators=[validators.DataRequired()])
    password = TextField('Password:', validators=[validators.DataRequired()])

class FileForm(FlaskForm):
    selectfile = SelectField('Filename', validators=[validators.DataRequired()])
    volunteersave = SubmitField(label='Submit File for Volunteers')
    slotsave = SubmitField(label='Submit File for Volunteer Shifts')
    eventsave = SubmitField(label='Submit File for Convention Events')
    eventsdelete = SubmitField(label='Delete All Convention Events')
    shiftsdelete = SubmitField(label='Delete All Volunteer Shifts ')
    daypartsdelete = SubmitField(label='Delete All Convention Day Parts')

class ConForm(FlaskForm):
    selectcon = SelectField('Convention', validators=[validators.DataRequired()])
    consubmit = SubmitField(label='Submit')

class LogoutForm(FlaskForm):
    logoutsubmit = SubmitField(label='Logout')

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
    # API Pull from TTE to get the convention information and urls needed to process the convention.
    con_params = {'session_id': ttesession['id'], "_include_relationships": 1}
    convention_response = requests.get(config.tte_url + "/convention/" + tteconvention_id, params= con_params)
    convention_data = convention_response.json()
    # API Pull from TTE to get the convention information
    event_params = {'session_id': ttesession['id'], "_include_relationships": 1, '_include': 'hosts'}
    event_response = requests.get('https://tabletop.events' + convention_data['result']['_relationships']['events'], params= event_params)
    event_data = event_response.json()
    for field in event_data['result']['items']:
        slot_url = field['_relationships']['slots']
        event_slots = get_slot_info(ttesession,slot_url)
        field['event_slots'] = event_slots
    # API Pull from TTE to get the volunteer information
    volunteer_field = convention_data['result']['_relationships']['volunteers']
    volunteer_params = {'session_id': ttesession['id']}
    volunteer_response = requests.get('https://tabletop.events' + volunteer_field, params = volunteer_params)
    volunteer_data = volunteer_response.json()
    # Populate dictionary with the info pulled from TTE
    convention_info['event'] = event_data
    convention_info['data'] = convention_data
    convention_info['volunteers'] = volunteer_data
    return(convention_info)

# -----------------------------------------------------------------------
# Pull Slot Data from the TTE API
# -----------------------------------------------------------------------
def get_slot_info(ttesession,slot_url):
    slot_params = {'session_id': ttesession['id']}
    slot_response = requests.get('https://tabletop.events' + slot_url, params= slot_params)
    slot_data = slot_response.json()
    slot_info = slot_data['result']['items']
    return(slot_info)

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
def volunteer_parse(filename,tteconvention_id):
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
            volunteer.hours = 12
        elif new_volunteer['hours'] == 'Hotel':
            volunteer.hours = 20
        else:
            try:
                volunteer.hours = int(new_volunteer['hours'])
            except TypeError:
                pass
        for field in new_volunteer:
            if 'slot' in field:
                slot_number = field.rsplit()
                slot_number = slot_number[1]
                if 'X' in new_volunteer[field]:
                    all_slots.append(slot_number)
        volunteer.slots = ','.join(all_slots)
        tteconventions.append(tteconvention_id)
        volunteer.conventions = ','.join(tteconventions)
        ttevolunteer_id = tte_user_api_pull(ttesession,new_volunteer['email'])
        if ttevolunteer_id is None:
            try:
                volunteer.tteid = tte_user_add(ttesession,new_volunteer['email'],new_volunteer['name'],tteconvention_id)
                db.session.merge(volunteer)
            except:
                logger.exception("Cannot save volunteer")
                db.session.rollback()
                saved = 'failed'
                return (saved)
        else:
            volunteer.tteid = ttevolunteer_id
    # If the volunteer exists in the TRI User Database already but, add the new tteconvention to their conventions list
    elif k in all_volunteers and tteconvention_id not in all_volunteers[k].tteconventions:
        old_volunteer = all_volunteers[k]
        tteconventions = old_volunteer.tteconventions
        tteconventions.append(tteconvention_id)
        old_volunteer.conventions = ','.join(tteconventions)
        ttevolunteer_id = tte_user_api_pull(ttesession,old_volunteer.email)
        if ttevolunteer_id is None:
            try:
                old_volunteer.tteid = tte_user_add(ttesession,old_volunteer.email,old_volunteer.name,tteconvention_id)
                db.session.merge(volunteer)
            except:
                logger.exception("Cannot save volunteer")
                db.session.rollback()
                saved = 'failed'
                return (saved)
        else:
            old_volunteer.tteid = ttevolunteer_id
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
    volunteer_params = {'session_id': ttesession['id']}
    volunteer_url = 'https://tabletop.events' + '/api/user' + '?query=' + volunteer_email
    volunteer_response = requests.get(volunteer_url, params= volunteer_params)
    volunteer_data = volunteer_response.json()
    try:
        volunteer_id = volunteer_data['result']['items'][0]['id']
    except:
        volunteer_id = None
    return(volunteer_id)

# -----------------------------------------------------------------------
# Add user to TTE
# -----------------------------------------------------------------------
def tte_user_add(ttesession,volunteer_email,volunteer_name,tteconvention_id):
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
        return()

# -----------------------------------------------------------------------
# Slot Functions
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# List all volunteers in database
# -----------------------------------------------------------------------
def list_slots(tteconvention_id):
    convention = Conventions()
    convention = Conventions.query.filter_by(tteid = tteconvention_id).first()
    slots = {}
    if convention.slots is not None:
        con_slots = json.loads(convention.slots)
        for slot in con_slots:
            try:
                new_slot = int(slot)
                slots[new_slot] = con_slots[slot]
            except ValueError:
                pass
    return(slots)

# -----------------------------------------------------------------------
# Parse the File for slots
# -----------------------------------------------------------------------
def slot_parse(filename,tteconvention_id,tteconvention_name):
    # Definitions
    slot = {}
    newheader = []
    # Open CSV file and verify headers
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for header in reader.fieldnames:
            if 'Slot' in header:
                header_l = header.rsplit()
                newheader.append('slot ' + header_l[1])
            if 'Length' in header:
                newheader.append('length')
        reader.fieldnames = newheader
        for slots_info in reader:
            slots_saved = slot_save(slots_info,tteconvention_id,tteconvention_name)
        return(slots_saved)

# -----------------------------------------------------------------------
# Save slots to database
# -----------------------------------------------------------------------
def slot_save(slots_info,tteconvention_id,tteconvention_name):
    all_slots = list_slots(tteconvention_id)
    new_convention = Conventions()
    new_slot = {}
    # Check the database to see if the slot already exists for the convention
    # Create the dict of slot time and length of each slot
    for field in slots_info:
        if 'slot' in field:
            slot_num = field.rsplit()
            new_slot[slot_num[1]] = slots_info[field], slots_info['length']
    conventions_slots = json.dumps(new_slot)
    new_convention.slots = conventions_slots
    new_convention.tteid = tteconvention_id
    new_convention.name = tteconvention_name
    db.session.merge(new_convention)
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
# Delete slots to database
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
# Post slots to TTE as Volunteer Shifts
# -----------------------------------------------------------------------
def tte_convention_volunteer_shift_api_post(ttesession,tteconvention_id,savedslots):
    tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
    # Get the information on Convention Days
    day_info = tte_convention_days_api_get(ttesession,tteconvention_id)

    # Verify if the "Slot Type" exists, if it doesn't, initialize the shifttype of "Slot" for tteid
    shifttypes_uri = 'https://tabletop.events' + tteconvention_data['data']['result']['_relationships']['shifttypes']
    shifttypes_get_params = {'session_id': ttesession, 'convention_id': tteconvention_id}
    shifttypes_get_response = requests.get(shifttypes_uri, params= shifttypes_get_params)
    shifttypes_get_data = shifttypes_get_response.json()
    shifttype_id = shifttypes_get_data['result']['items'][0]['id']

    # For each slot, get the information we need to be able to post the slot as a shift
    for slot in savedslots:
        slot_length = int(savedslots[slot][1])
        shift_name = 'Slot ' + str(slot)
        shift_time_s = savedslots[slot][0]
        shift_start = datetime.datetime.strptime(shift_time_s, '%m/%d/%y %I:%M:%S %p')
        shift_end = shift_start + datetime.timedelta(hours=slot_length)
        for day in day_info:
            slot_date = datetime.date(shift_start.year,shift_start.month,shift_start.day)
            shift_date = datetime.date(day['day_time'].year,day['day_time'].month,day['day_time'].day)
            # Compare the dates of the slot and the shift to get the tteid to use to post the shift
            if slot_date == shift_date:
                shift_id = day['id']
                shift_params = {'session_id': ttesession['id'], 'convention_id': tteconvention_id, 'name': shift_name, 'quantity_of_volunteers': '255', 'start_time': shift_start, 'end_time': shift_end, 'conventionday_id': shift_id, 'shifttype_id': shifttype_id}
                shift_response = requests.post(config.tte_url + '/shift', params= shift_params)
                shift_data = shift_response.json()
                print (shift_data)
    return('saved')
# -----------------------------------------------------------------------
# API Post to TTE for Volunteer Shifts
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# Post slots to TTE as Day Parts
# -----------------------------------------------------------------------
def tte_convention_dayparts_api_post(ttesession,tteconvention_id,savedslots):
    #Declarations
    slots = {}
    # Get data on the days
    day_info = tte_convention_days_api_get(ttesession,tteconvention_id)

    # Convert slots data to datetime
    for slot in savedslots:
        slot_time_s = savedslots[slot][0]
        slot_start = datetime.datetime.strptime(slot_time_s, '%m/%d/%y %I:%M:%S %p')
        slot_length = savedslots[slot][1]
        slots[slot]= {'slot_time': slot_start, 'slot_length': slot_length}

    # Loop through the day in 30 minute increments
    for day in day_info:
        day_id = day['id']
        day_start = day['day_time']
        day_end = day['end_time']
        daypart_time = day_start
        print (day_start,day_end)
        while daypart_time < day_end:
            daypart_name = datetime.datetime.strftime(slot_start, '%a %I:%M %p')
            slot_start = daypart_time
            print(slot_start,daypart_name)
            daypart_time = daypart_time + datetime.timedelta(minutes= 30)
            # API Post to TTE (Day Parts)
            daypart_params = {'session_id': ttesession['id'], 'convention_id': tteconvention_id, 'name': daypart_name, 'start_date': slot_start, 'conventionday_id': day_id}
            daypart_response = requests.post(config.tte_url + '/daypart', params= daypart_params)
            daypart_data = daypart_response.json()
            print (daypart_data)
    return('saved')

# -----------------------------------------------------------------------
# Pull TTE Volunteer Shifts
# -----------------------------------------------------------------------
def tte_convention_volunteer_shift_api_get(ttesession,tteconvention_id):
    tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
    tteconvention_shift_uri = 'https://tabletop.events' + tteconvention_data['data']['result']['_relationships']['shifts']
    shift_get_params = {'session_id': ttesession['id']}
    shift_get_response = requests.get(tteconvention_shift_uri, params= shift_get_params)
    shift_get_data = shift_get_response.json()
    all_shifts = shift_get_data['result']['items']
    return(all_shifts)

# -----------------------------------------------------------------------
# Delete all shifts from TTE
# -----------------------------------------------------------------------
def tte_convention_volunteer_shift_api_delete(ttesession,tteconvention_id,all_shifts):
    for shift in all_shifts:
        shift_delete_params = {'session_id': ttesession['id']}
        shift_delete_url = 'https://tabletop.events/api/shift/' + shift['id']
        shift_delete_response = requests.delete(shift_delete_url, params= shift_delete_params)
        shift_delete_data = shift_delete_response.json()
        print(shift['id'],shift_delete_data)
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
            elif 'Date' in header:
                newheader.append('date_info')
            elif 'Start Time' in header:
                newheader.append('starttime')
            elif 'Duration' in header:
                newheader.append('duration')
            elif 'Table Count' in header:
                newheader.append('tablecount')
            elif 'Hosts' in header:
                newheader.append('hosts')
            elif 'Type' in header:
                newheader.append('type')
        reader.fieldnames = newheader
        for event in reader:
            savedevents.append(event)
        return(savedevents)

# -----------------------------------------------------------------------
# Push Events to TTE
# -----------------------------------------------------------------------
def tte_convention_events_api_post(ttesession,tteconvention_id,savedevents):
    event_hosts_l = []

    tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
    type_id_url = tteconvention_data['data']['result']['_relationships']['eventtypes']
    days_url = tteconvention_data['data']['result']['_relationships']['days']
    #Get the event types
    type_id_params = {'session_id': ttesession['id']}
    type_id_response = requests.get('https://tabletop.events' + type_id_url, params= type_id_params)
    type_id_data = type_id_response.json()
    event_types = type_id_data['result']['items']
    #Get the convention days
    convention_days = tte_convention_days_api_get(ttesession,tteconvention_id)
    #Get the dayparts for the convention
    convention_dayparts = tte_convention_dayparts_api_get(ttesession,tteconvention_id)

    for event in savedevents:
        # Define the list of hosts for the event
        host_id_l = []
        event_hosts_l = event['hosts'].split(' ')
        for host in event_hosts_l:
            try:
                host_id = tte_user_api_pull(ttesession,host)
                host_id_l.append(host_id)
                print(host,host_id)
            except:
                print(host,host_id,' Failure')
                pass
        # Compare the Name of the type with the provided Event Type
        # If they match, return the TTE ID of the Type
        for type in event_types:
            if event['type'] == type['name']:
                event['type_id'] = type['id']

        # Calculate the datetime value of the event
        event['duration'] = int(event['duration'])
        event['datetime_s'] = event['date_info'] + ' ' + event['starttime']
        event['datetime'] = datetime.datetime.strptime(event['datetime_s'],'%m/%d/%y %I:%M %p')

        # Identify the Day Id for the convention
        for day in convention_days:
            day['date_check'] = datetime.date(day['day_time'].year,day['day_time'].month,day['day_time'].day)
            event['date_check'] = datetime.date(event['datetime'].year,event['datetime'].month,event['datetime'].day)
            if event['date_check'] == day['date_check']:
                event['day_id'] = day['id']

        # Identify the datetime value of the dayparts
        # Then compare to see if they are equal to determine the TTE ID of the time
        for dayparts in convention_dayparts:
            if event['datetime'] == dayparts['datetime']:
                event['dayparts_id'] = dayparts['id']

        if event['day_id'] and event['type_id'] and event['dayparts_id']:
            # Create the Event
            event_params = {'session_id': ttesession['id'], 'convention_id': tteconvention_id, 'name' : event['name'], 'max_tickets' : 6, 'priority' : 3, 'age_range': 'all', 'type_id' : event['type_id'], 'conventionday_id' : event['day_id'], 'duration' : event['duration'], 'alternatedaypart_id' : event['dayparts_id'], 'preferreddaypart_id' : event['dayparts_id']}
            event_response = requests.post('https://tabletop.events/api/event', params= event_params)
            event_data = event_response.json()
            event['id'] = event_data['result']['id']
            # Add hosts to the Event
            for host in host_id_l:
                if host is not None:
                    host_params = {'session_id': ttesession['id'] }
                    print ('Event: ', event['id'], ' Host: ', host)
                    host_url = 'https://tabletop.events/api/event/' + event['id'] + '/host/' + host
                    host_response = requests.post(host_url, params= host_params)
                    host_data = host_response.json()
    return()

# -----------------------------------------------------------------------
# Delete all Events for the Convention
# -----------------------------------------------------------------------
def tte_convention_events_api_delete(ttesession,tteconvention_id,allevents):
    tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
    for event in allevents:
        event_delete_params = {'session_id': ttesession['id']}
        event_delete_url = 'https://tabletop.events/api/event/' + event['id']
        event_delete_response = requests.delete(event_delete_url, params= event_delete_params)
        event_delete_data = event_delete_response.json()
        print(event['id'],event_delete_data)
    return()

# -----------------------------------------------------------------------
# Get days of the convention
# -----------------------------------------------------------------------
def tte_convention_days_api_get(ttesession,tteconvention_id):
    #Declarations
    day_info = []
    # Get the data on the convention
    tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
    tteconvention_days_uri = 'https://tabletop.events' + tteconvention_data['data']['result']['_relationships']['days']
    # Use the day url to get data on the days
    day_params = {'session_id': ttesession, 'convention_id': tteconvention_id}
    day_response = requests.get(tteconvention_days_uri, params= day_params)
    day_data = day_response.json()
    # Create a datetime value for each day, add to a new dict
    for item in day_data['result']['items']:
         dt = datetime.datetime.strptime(item['start_date'], '%Y-%m-%d %H:%M:%S')
         et = datetime.datetime.strptime(item['end_date'], '%Y-%m-%d %H:%M:%S')
         day_info.append({'id' : item['id'], 'day_time' : dt, 'end_time': et})
    return(day_info)

# -----------------------------------------------------------------------
# Get the id for day parts
# -----------------------------------------------------------------------
def tte_convention_dayparts_api_get(ttesession,tteconvention_id):
    day_parts_start = 1
    day_parts_total = 100
    all_dayparts = list()
    tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
    dayparts_url = tteconvention_data['data']['result']['_relationships']['dayparts']

    while day_parts_total >= day_parts_start:
        dayparts_params = {'session_id': ttesession['id'], '_page_number': day_parts_start}
        dayparts_response = requests.get('https://tabletop.events' + dayparts_url, params= dayparts_params)
        dayparts_data = dayparts_response.json()
        convention_dayparts = dayparts_data['result']['items']
        for dayparts in convention_dayparts:
            dayparts['datetime'] = datetime.datetime.strptime(dayparts['start_date'],'%Y-%m-%d %H:%M:%S')
            all_dayparts.append(dayparts)
        if day_parts_start < day_parts_total:
            day_parts_start = int(dayparts_data['result']['paging']['next_page_number'])
            day_parts_total = int(dayparts_data['result']['paging']['total_pages'])
        elif day_parts_start == day_parts_total:
            day_parts_total = int(dayparts_data['result']['paging']['total_pages'])
            day_parts_start = day_parts_total + 1
        else:
            pass
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
        print(daypart['id'],daypart_delete_data)
    return()

# -----------------------------------------------------------------------
# Get Table Information
# -----------------------------------------------------------------------
def tte_convention_spaces_id_api_get(ttesession,tteconvention_id):
    rooms = {}
    spaces = {}
    tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
    spaces_url = tteconvention_data['data']['result']['_relationships']['spaces']
    space_params = {'session_id': ttesession['id']}
    space_response = requests.get('https://tabletop.events' + spaces_url, params= space_params)
    space_data = space_response.json()
    return(space_data)

# -----------------------------------------------------------------------
# Get all events for Convention
# -----------------------------------------------------------------------
def tte_convention_events_api_get(ttesession,tteconvention_id):
    tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
    events_start = 1
    events_total = 100
    all_events = list()

    while events_total >= events_start:
        events_url = tteconvention_data['data']['result']['_relationships']['events']
        events_params = {'session_id': ttesession['id'], 'tteconvention_id': tteconvention_id, '_page_number': events_start}
        events_response = requests.get('https://tabletop.events' + events_url,params= events_params)
        events_data = events_response.json()
        convention_events = events_data['result']['items']
        for events in convention_events:
            all_events.append(events)
        if events_start < events_total:
            events_start = int(events_data['result']['paging']['next_page_number'])
            events_total = int(events_data['result']['paging']['total_pages'])
        elif events_start == events_total:
            events_total = int(events_data['result']['paging']['total_pages'])
            events_start = events_total + 1
        else:
            pass
    return(all_events)
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
    savedslots = {}
    savedvolunteers = {}
    savedevents = {}
    # Form Function calls
    conform = ConForm(request.form, obj=tteconventions)
    conform.selectcon.choices = [(tteconventions[con]['id'],tteconventions[con]['name']) for con in tteconventions]
    fileform = FileForm(request.form, obj=files)
    fileform.selectfile.choices = [(file,file) for file in files]
    if request.method == "POST":
        # Pull all the data regarding the convention
        if request.form.get('consubmit'):
            session['tteconvention_id'] = request.form.get('selectcon',None)
            tteconvention_data = tte_convention_api_pull(ttesession,session['tteconvention_id'])
            tteconvention_name = tteconvention_data['data']['result']['name']
            savedvolunteers = list_volunteers(session['tteconvention_id'])
            savedslots = list_slots(session['tteconvention_id'])
            ttedayparts = tte_convention_dayparts_api_get(ttesession,tteconvention_id)
#            savedevents = list_events(session['tteconvention_id'])
            rooms = tte_convention_spaces_id_api_get(ttesession,session['tteconvention_id'])
            return render_template('conventions.html', conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            'ttedayparts' : ttedayparts,
            'savedvolunteers' : savedvolunteers,
            'savedslots' : savedslots
            })
        if request.form.get('volunteersave') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
            tteconvention_name = tteconvention_data['data']['result']['name']
            # Volunteer Management
            volunteerselect = request.form.get('selectfile')
            location = os.path.join(folder,volunteerselect)
            volunteers = volunteer_parse(location,tteconvention_id)
            return render_template('conventions.html', conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            'savedvolunteers' : savedvolunteers
            })
        if request.form.get('slotsave') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
            tteconvention_name = tteconvention_data['data']['result']['name']
            # Slot Management
            slotselect = request.form.get('selectfile')
            location = os.path.join(folder,slotselect)
            saved = slot_parse(location,tteconvention_id,tteconvention_name)
            savedslots = list_slots(tteconvention_id)
            #pushshifts = tte_convention_volunteer_shift_api_post(ttesession,tteconvention_id,savedslots)
            pushdayparts = tte_convention_dayparts_api_post(ttesession,tteconvention_id,savedslots)
            return render_template('conventions.html', conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            'savedslots' : savedslots
            })
        if request.form.get('eventsave') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
            tteconvention_name = tteconvention_data['data']['result']['name']
            eventselect = request.form.get('selectfile')
            location = os.path.join(folder,eventselect)
            savedevents = event_parse(location,tteconvention_id,tteconvention_name)
            pushevents = tte_convention_events_api_post(ttesession,tteconvention_id,savedevents)
            return render_template('conventions.html', conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            'savedevents' : savedevents
            })
        if request.form.get('eventsdelete') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
            tteconvention_name = tteconvention_data['data']['result']['name']
            tteevents = tte_convention_events_api_get(ttesession,tteconvention_id)
            deleteevents = tte_convention_events_api_delete(ttesession,tteconvention_id,tteevents)
            return render_template('conventions.html', conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            'savedevents' : savedevents
            })
        if request.form.get('shiftsdelete') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
            tteconvention_name = tteconvention_data['data']['result']['name']
            tteshifts = tte_convention_volunteer_shift_api_get(ttesession,tteconvention_id)
            deleteshifts = tte_convention_volunteer_shift_api_delete(ttesession,tteconvention_id,tteshifts)
            savedslots = list_slots(tteconvention_id)
            databaseslotdelete = database_slot_delete(tteconvention_id)
            return render_template('conventions.html', conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            })
        if request.form.get('daypartsdelete') and session.get('tteconvention_id') is not None:
            tteconvention_id = session.get('tteconvention_id')
            tteconvention_data = tte_convention_api_pull(ttesession,tteconvention_id)
            tteconvention_name = tteconvention_data['data']['result']['name']
            ttedayparts = tte_convention_dayparts_api_get(ttesession,tteconvention_id)
            deletedayparts = tte_convention_dayparts_api_delete(ttesession,tteconvention_id,ttedayparts)
            return render_template('conventions.html', conform=conform, fileform=fileform, **{'name' : name,
            'tteconventions' : tteconventions,
            'tteconvention_name' : tteconvention_name,
            'tteconvention_data' : tteconvention_data,
            })
        else:
            return render_template('conventions.html', conform=conform, fileform=fileform, **{'name' : name })

    else:
        return render_template('conventions.html', conform=conform, fileform=fileform, **{'name' : name,
        })
# -----------------------------------------------------------------------
# Run Program
# -----------------------------------------------------------------------
if __name__ == '__main__':
    app.run(port=config.PORT, host=config.HOST)
