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
