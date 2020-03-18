# -----------------------------------------------------------------------
# Schedule Creator Addon
# -----------------------------------------------------------------------
def create_schedule(ttesession,tteconvention_id):
    class Volunteer:
        def __init__(self,name,id):
            self.name = name
            self.id = id
            self.events = []
            self.shifts = []
            self.dayparts = []
            self.types = []
            self.tiers = []

        def add_event(self,event):
            self.events.append(event)
        def add_shift(self,shift):
            self.shifts.append(shift)
        def add_dayparts(self,dayparts):
            self.dayparts.extend(daypart)
        def add_tier(self,tier):
            self.tiers.append(tier)
        def add_type(self,type):
            self.types.append(type)

    class Event:
        def __init__(self,name,id):
            self.name = name
            self.id = id
            self.dayparts = []

        def add_dayparts(self,daypart):
            self.dayparts.extend(dayparts)

        def add_time(self,time):
            self.time = self.time + time

    class Shift:
        def __init__(self,name,id,type,start_time,end_time,duration):
            self.name = name
            self.id = id
            shift.type = type
            shift.start_time = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            shift.end_time = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
            shift.duration = datetime.datetime.timedelta(hours=duration)
            self.dayparts = []

    class Daypart:
        def __init__(self,name,id):
            self.name = name
            self.id = id


    #Iterate through the volunteers pulled from TTE to create Volunteer Objects
    for volunteer in tteconvention_data['volunteers']:
        new_volunteer = Volunteer(volunteer['name'],volunteer['id'])
        vol_events = tte_user_events_api_get(ttesession,volunteer['id'])
        # Iterate through the volunteer scheduled events to generate a list of the dayparts already scheduled
        for vol_event in vol_events:
            volunteer_event = Event(vol_event['name'],vol_event['id'])
            vol_event_dayparts = tte_eventdayparts_api_get(ttesession,tteconvention_id,event['id'])
            # Iterate throught the eventdayparts to generate the daypart Objects
            for vol_event_daypart in vol_event_dayparts:

            volunteer_event.add_dayparts()
            new_volunteer.add_dayparts(volunteer_event.dayparts)

        vol_shifts = add_shifts(tte_volunteer_shifts_api_get(ttesession,tteconvention_id,volunteer['id']))
        # Iterate through the volunteer shifts to generate a list of dayparts currently available
        for vol_shift in vol_shifts:
            volunteer_shift = Shift(vol_shift['name'],vol_shift['id'],vol_shift['shifttype_id'],vol_shift['start_time'],vol_shift['end_time'],vol_shift['duration_in_hours'])





        for event in tteconvention_data['events']:
            new_event = Event(event['name'],event['id'])
            new_event.add_dayparts(tte_eventdayparts_api_get(ttesession,tteconvention_id,event['id']))
            matching_dayparts =


















    # Pull the information regarding the volunteer shifts in the convention
    convention_shifts = tte_convention_volunteer_shifts_api_get(ttesession,tteconvention_id)
    # Pull the information regarding the volunteer shifttypes in the convention
    convention_shift_types = tte_convention_volunteer_shifttypes_api_get(ttesession,tteconvention_id)
    # Pull the information regarding the days of each convention
    convention_days = tte_convention_days_api_get(ttesession,tteconvention_id)
    # Pull the information of each of the dayparrts of the convention
    convention_dayparts = tte_convention_dayparts_api_get(ttesession,tteconvention_id)
    # Pull the information regarding the dayparts that comprise the event
    event_dayparts = tte_eventdayparts_api_get(ttesession,tteconvention_id,event_id)
    # Iterate through the types of shifts and the shifts in the convention to get the tteid(s) of the shift(s) that cover the event
    for type in convention_shift_types:
        for shift in convention_shifts:
            if shift['shifttype_id'] == type['id']:
                shift['type_name'] = type['name']
            while event['shift_durations'] != event['duration']:
                if shift['start_time'] == event['start_date'] and shift['type_name'] == event_type:
                    shift['start_time'] = datetime.datetime.strptime(shift['start_time'], '%Y-%m-%d %H:%M:%S')
                    shift['end_time'] = datetime.datetime.strptime(shift['end_time'], '%Y-%m-%d %H:%M:%S')
                    shift_td = shift['end_time'] - shift['start_time']
                    shift['duration'] = int(shift_td.seconds / 60)
                    event['shift_durations'] = event['shift_durations'] + shift['duration']
                    event['next_shift_time'] = shift['end_time']
                    event['shifts'].append(shift)
                elif shift['start_time'] == event['next_shift_time'] and shift['type_name'] == event_type:
                    shift['end_time'] = datetime.datetime.strptime(shift['end_time'], '%Y-%m-%d %H:%M:%S')
                    shift_td = shift['end_time'] - event['next_shift_time']
                    shift['duration'] = int(shift_td.seconds / 60)
                    event['shift_durations'] = event['shift_durations'] + shift['duration']
                    event['next_shift_time'] = shift['end_time']
                    event['shifts'].append(shift)
    # Itereate through the volunteers as many times as there are tables for the event to compare all volunteer information with the event information to add the volunteer as a host to an event
    for tc in range(1,event_tablecount,1):
        for volunteer in convention_data['volunteers']:
            volunteer_dayparts_scheduled = []
            # Get the shifts the volunteer applied for
            volunteer['shifts'] = tte_volunteer_shifts_api_get(ttesession,tteconvention_id,volunteer['user_id'])
            # Get any events already hosted by the volunteer
            volunteer['events'] = tte_user_events_api_get(ttesession,volunteer['user_id'])
            # If there are events already scheduled, get the daypart ids that the events span
            if len(volunteer['events']) != 0:
                for volunteer_event in volunteer['events']:
                    volunteer_event['detail'] = tte_event_api_get(ttesession,tteconvention_id,volunteer_event['event_id'])
                    volunteer_event_dayparts = tte_eventdayparts_api_get(ttesession,tteconvention_id,volunteer_event['event_id'])
                    volunteer_dayparts_scheduled.extend(volunteer_event_dayparts)
                else:
                    pass
            volunteer['scheduled_dayparts'] = volunteer_dayparts_scheduled
            # Verify adding the event to the volunteers schedule won't put them over 8 hours.
            volunter_time = len(volunteer['scheduled_dayparts']) * 30
            event_time =
            if volunter_time + =>
            # Find if there are matches between the volunteer shift ids and the event shift ids
            for volunteer_shift in volunteer['shifts']:
                for event_shift in event['shifts']:
                    if volunteer_shift['id'] == event_shift['id']:


                        # Make sure the dayparts of the volunteer's events don't conflict with the dayparts of the event attempting to be scheduled


                                if volunteer_event_daypart['id'] in event_dayparts:
                                    # Calculate how much time the event is in minutes
                                    for event_daypart in event_dayparts:
                                        volunteer['maxtime'] = volunteer['maxtime'] + 30
                                    if volunteer['maxtime'] < 480:
                                        # host_data = tte_event_host_post(ttesession,event_id,volunteer['id'])
                                else:
                                    volunteer['maxtime'] = volunteer['maxtime'] + 30
                                if volunteer_event_daypart_count < 1:



                        else:
                            host_data = tte_event_host_post(ttesession,event_id,volunteer['id'])
    return(host_data)




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
            all_user_events.append(user_events_data)
        if user_events_start < user_events_total:
            user_events_start = int(user_events_data['result']['paging']['next_page_number'])
        elif user_events_start == user_events_total:
            break
        else:
            break
    return(all_user_events)
