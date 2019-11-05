# -*- encoding: utf-8 -*-
import datetime

# -----------------------------------------------------
# Application configurations
# ------------------------------------------------------

DEBUG = True
PORT = 8086
HOST = '0.0.0.0'
ALLOWED_EXTENSIONS = set(['csv'])
SECRET_KEY = '7d441f27d441f27567d441f2b6173269'
UPLOAD_FOLDER = '/var/wwwTRITTEAPI/uploads'

# -----------------------------------------------------
# TTE defaults configurations
# ------------------------------------------------------
tte_url="https://tabletop.events/api"
tte_api_key_id = '0A4DCD00-ED07-11E9-B27C-43B2D530A4B6'
tte_username = 'eric.boaen@theroleinitiative.o'
tte_password = 'Unobtainium1'
tte_group_id = 'B3124686-B852-11E8-AB7F-B79E49AF76B9'

# -----------------------------------------------------
# SQL Alchemy configs
# -----------------------------------------------------
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://triadmin:Ch4mp10n@0.0.0.0/trischedule'
SQLALCHEMY_ECHO = False
# ------------------------------------------------------
# DO NOT EDIT
# Fix warnings from flask-sqlalchemy / others
# ------------------------------------------------------
SQLALCHEMY_TRACK_MODIFICATIONS = True
