# TRITTEAPI
TRI Tabletop.Events API extension

Scope document

Login Page
    * User Object
      - email address
      - password

Welcome Page
    * Convention Object
      - API pull/push
      - Name
      - ID
      - uri
      - time/dates

Convention Page
* timeslot creation, ingest as tte shifts, save to database
* volunteer import, ingest as tte volunteer, save to database
* event import, ingest as tte events, save to database

    * Volunteer Object
      - Name
      - email address
      - location
      - slots available
        - Volunteer in use/not in use by Event

    * Slot Object
      - API pull/push
      - Datetime start and finish

    * Table Object
      - API pull/push
      - slot availability
        - Table in use/not in use by Event

    * Event Object
      - API pull/push
      - Name
      - Code (Optional)
      - Length of Event
      - Asigned Slot(s)
      - Assigned Table(s)
        - Reads Table Object for availability during assigned slot(s)
        - Updates Table Object for availability during assigned slot(s)
      - Assigned Host(s)
        - Uses Volunteer Object to determine if Volunteer is available during slot to host
        - Updates Volunteer Object once assigned to a Slot to make that Volunteer no longer available for that Slot




Extras:
  * Auto-generation of volunteer schedule
