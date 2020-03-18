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
    return(all_events)

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