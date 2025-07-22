def create_event_list(text):

    event = {}
    event_list = [
        event,
        event,
        event,
    ]

    return event_list


def get_access_token(code):
    access_token = ""
    return access_token


def create_event(event, access_token):
    pass


def create_events_in_calendar(text, code):

    event_list = create_event_list(text)

    access_token = get_access_token(code)

    for event in event_list:

        create_event(event, access_token)
