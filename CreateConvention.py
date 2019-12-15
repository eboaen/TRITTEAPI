# -----------------------------------------------------------------------
# Forms
# -----------------------------------------------------------------------
class NewConventionForm(FlaskForm):
    name = StringField('New Convention Name:', validators=[validators.DataRequired()])
    location = StringField('City, Sate of the Convention', validators=[validators.DataRequired()])
    description = TextAreaField('Description of the Convention', validators=[validators.DataRequired()])
    phone_number = StringField('Please provide your phone number for volunteers to contact you at', validators=[validators.DataRequired()])
    dates = TextAreaField('List each date of the Convention, date per line', validators=[validators.DataRequired()])
    volunteer_greeting = TextAreaField('Give the volunteer greeting', validators=[validators.DataRequired()])

# -----------------------------------------------------------------------
# New Convention Route
# -----------------------------------------------------------------------
@app.route('/newconvention', methods=['GET', 'POST', 'PUT'])
def create_convention():
    # Declarations
    new_convention = {}
    # Call the global so we can modify it in the function with the API call.
    ttesession = session.get('ttesession')
    # Form Function calls
    newconventionform = NewConventionForm(request.form)
    if request.method == "POST":
        new_convention['name'] = request.newconventionform['name']
        new_convention['location'] = request.newconventionform['location']
        new_convention['description'] = request.newconventionform['description']
        new_convention['phone_number'] = request.newconventionform['phone_number']
        new_convention['dates'] = request.newconventionform['dates']
        new_convention['volunteer_greeting'] = request.newconventionform['volunteer_greeting']
        if form.validate():
            print ('Creating Convention')
            tte_convention_convention_api_post(ttesession,new_convention)
            return render_template('newconvention.html', newconventionform=newconventionform, newconvention_data)
    return render_template('newconvention.html', newconventionform=newconventionform)

# -----------------------------------------------------------------------
# Creat a new Convention
# -----------------------------------------------------------------------
def tte_convention_convention_api_post(ttesession,new_convention)
    # Declarations
    # Shorten the geonamescache call
    gc = geonamescache.GeonamesCache()
    # Define countries, usstates, and cities
    countries = gc.get_countries()
    usstates = gc.get_us_states()
    cities = gc.get_cities()

    # Get the location defined by the user
    location = new_convention['location'].split(', ')
    possible_city = location[0]
    website_uri = 'https://theroleinitiative.org'
    # Check to see if the user entered in a valid city/state or city/country combination
    # If it matches, call the functions to get the geo tte id or create a new location and return it's geo tte id
    if location[0] in cities and location[1] in usstates:
        try:
            geolocation_id = tte_geolocation_api_get(ttesession,new_convention)
        except:
            geolocation_id = tte_geolocation_api_post(ttesession,new_convention)
    elif location[0] in cities and location[1] in countries:
        try:
            geolocation_id = tte_geolocation_api_get(ttesession,new_convention)
        except:
            geolocation_id = tte_geolocation_api_post(ttesession,new_convention)
    else:
        flash('Please enter a valid location in the format of City, State or City, Country')
        return redirect(request.url)
    # Define parameters to create the convention
    convention_url = '/api/convention'
    convention_params = {
                        'session_id': ttesession['id'],
                        'name': new_convention['location'],
                        'facebook_page': 'https://www.facebook.com/theroleinitiative/',
                        'generic_ticket_price': 0,
                        'group_id': config.tte_group_id,
                        'slot_duration': 30,
                        'twitter_handle': '@_roleinitiative',
                        'email_address': 'events@theroleinitiative.org',
                        'phone_number': new_convention['phone_number'],
                        'geolocation_id': geolocation_id,
                        'volunteer_scheduled_greeting': new_convention['volunteer_greeting'],
                        'volunteer_custom_fields': [
                            {
                                "required" : 1,
                                "label" : "Emergency Contact: Name, phone number, relationship",
                                "name" : "volunteeremergencycontact",
                                "edit" : 0,
                                "type" : "text",
                                "conditional" : 0,
                                "view" : 1,
                                "sequence_number" : 3
                             },
                             {
                                "required" : 0,
                                "label" : "Previous Convention/D&D Volunteer experience",
                                "type" : "textarea",
                                "conditional" : 0,
                                "name" : "volunteerexperience",
                                "edit" : 0,
                                "sequence_number" : 2,
                                "view" : 1
                             },
                             {
                                "view" : 1,
                                "sequence_number" : 4,
                                "edit" : 0,
                                "name" : "volunteerlevel",
                                "type" : "select",
                                "conditional" : 0,
                                "options" : "Hotel\n4 Day\n1 day\n1 slot",
                                "label" : "Volunteer Level - Hotel level requires committing to 24 hours over the 4 days of the convention.  Badge Level requires 12 hours, Day level requires 4 hours.  1 slot is 2 hours.  At this time we cannot confirm Hotels Slots will be available for the convention, but if you are interested in volunteering at that level still select that as an option please.",
                                "required" : 1
                             },
                             {
                                "required" : 0,
                                "label" : "Shirt Size",
                                "options" : "S\nM\nL\nXL\nXXL\n3X\n4X\n5X",
                                "type" : "select",
                                "conditional" : 0,
                                "name" : "volunteershirtsize",
                                "edit" : 0,
                                "view" : 1,
                                "sequence_number" : 7
                             },
                             {
                                "label" : "Other comments (accommodations requests, allergies we should be aware of, other things you feel you should share, etc.)",
                                "required" : 0,
                                "type" : "textarea",
                                "conditional" : 0,
                                "edit" : 0,
                                "name" : "volunteerother",
                                "sequence_number" : 11,
                                "view" : 1
                             },
                             {
                                "sequence_number" : 9,
                                "view" : 1,
                                "conditional" : 0,
                                "type" : "text",
                                "edit" : 0,
                                "name" : "volunteerlocation",
                                "label" : "Where are you coming from (City/State)",
                                "required" : 1
                             },
                             {
                                "view" : 1,
                                "sequence_number" : 1,
                                "required" : 0,
                                "label" : "What pronouns do you use for yourself?",
                                "name" : "volunteerpronouns",
                                "edit" : 0,
                                "conditional" : 0,
                                "type" : "text"
                             },
                             {
                                "sequence_number" : 8,
                                "view" : 1,
                                "edit" : 0,
                                "name" : "volunteersource",
                                "conditional" : 0,
                                "type" : "text",
                                "label" : "How did you hear about us?",
                                "required" : 1
                             },
                             {
                                "options" : "None\n1\n2\n3\n4",
                                "required" : 1,
                                "label" : "Tier (What is the highest Tier you are comfortable GMing, enter None if you do not want to GM at all)",
                                "name" : "volunteertiers",
                                "edit" : 0,
                                "conditional" : 0,
                                "type" : "select",
                                "sequence_number" : 6,
                                "view" : 1
                             },
                             {
                                "sequence_number" : 10,
                                "view" : 1,
                                "conditional_name" : "volunteerlevel",
                                "edit" : 0,
                                "conditional_value" : "Hotel",
                                "name" : "volunteerhotelpref",
                                "conditional" : 1,
                                "type" : "select",
                                "options" : "Male\nFemale\nAny",
                                "label" : "Hotel Rooming Preference",
                                "required" : 0
                             },
                             {
                                "view" : 1,
                                "sequence_number" : 5,
                                "required" : 1,
                                "label" : "What role are you interested in?  Admin roles are as follows: Runners work with the Admins assigned to the slot, they will help GMs with getting their badges and perform health checks.  Admins will help seat players at tables and check DMs in.  Head admin will be the escalation point for any issues that arise.",
                                "options" : "DM - Adventurers League Only\nDM - Acquisitions Incorporated Only\nDM - Any\nAdmin\nAny",
                                "conditional" : 0,
                                "type" : "select",
                                "name" : "volunteerrole",
                                "edit" : 0
                             }
                         ]
                        }
    convention_response = requests.post('https://tabletop.events', params= convention_params)
    convention_json = convention_response.json()
    convention_id = convention_json['result']['id']
    return(convention_id)

# -----------------------------------------------------------------------
# Query for a location id
# -----------------------------------------------------------------------
def tte_geolocation_api_get(ttesession,new_convention)
    geolocation_url = '/api/geolocation' + '?query=' + new_convention['location']
    geolocation_params = {'session_id': ttesession['id']}
    geolocation_response = requests.get('https://tabletop.events' + geolocation_url, params= geolocation_params)
    geolocation_json = geolocation_response.json()
    geolocation_id = geolocation_data['result']['id']
    return(geolocation_id)

# -----------------------------------------------------------------------
# Create a new location
# -----------------------------------------------------------------------
def tte_geolocation_api_post(ttesession,new_convention)
    geolocation_url = '/api/geolocation'
    geolocation_params = {'session_id': ttesession['id'], 'name': new_convention['location']}
    geolocation_response = requests.post('https://tabletop.events', params= geolocation_params)
    geolocation_json = geolocation_response.json()
    geolocation_id = geolocation_json['result']['id']
    return(geolocation_id)
