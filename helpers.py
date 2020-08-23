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
