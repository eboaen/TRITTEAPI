# -----------------------------------------------------------------------
# Schedule Creator Addon
# -----------------------------------------------------------------------
def create_schedule(ttesession,tteconvention_id,event_tablecount,event):
    class volunteer:
        def __init__(self,name):
            self.name
        def add_event(self,event):
            self.events.append(event)
        def add_shift(self,shift):
            self.shifts.append(shift)
        def





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
