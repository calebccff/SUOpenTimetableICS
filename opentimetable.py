import requests
import json
from ics import Calendar, Event
from urllib.parse import quote
from datetime import datetime, timedelta
from arrow import Arrow

# Reference: https://github.com/Frazl/dcu-opentimetable/blob/2e1b8a8966e7573118587e6d04a3a3dbfe98eae4/timetable.py

HEADERS = {
    "Authorization": "basic kR1n1RXYhF",
    "Content-Type" : "application/json",
    "Referer" : "https://opentimetables.swan.ac.uk/",
    "Origin" : "https://opentimetables.swan.ac.uk/",
    "Host": "opentimetables.swan.ac.uk",
    "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
}

BASE_URL = "https://opentimetables.swan.ac.uk/broker/api/CategoryTypes/525fe79b-73c3-4b5c-8186-83c652b3adcc/"

def get_view_options(weeks=20):
    view_options = {
        "Days": [
            {
                "Name": "Monday",
                "DayOfWeek": 1,
                "IsDefault": True
            },
            {
                "Name": "Tuesday",
                "DayOfWeek": 2,
                "IsDefault": True
            },
            {
                "Name": "Wednesday",
                "DayOfWeek": 3,
                "IsDefault": True
            },
            {
                "Name": "Thursday",
                "DayOfWeek": 4,
                "IsDefault": True
            },
            {
                "Name": "Friday",
                "DayOfWeek": 5,
                "IsDefault": True
            }
        ],
        "Weeks": [],
        "TimePeriods": [
            {
                "Description": "Teaching Day",
                "StartTime": "09:00",
                "EndTime": "18:00",
                "IsDefault": True
            }
        ],
        "DatePeriods": [
            {
                "Description": "This Week",
                "StartDateTime": "2022-09-26T00:00:00.000Z",
                "EndDateTime": "2023-09-25T00:00:00.000Z",
                "IsDefault": True,
                "IsThisWeek": True,
                "IsNextWeek": False,
                "Type": "ThisWeek"
            }
        ],
        "LegendItems": [],
        "InstitutionConfig": {},
        "DateConfig": {
            "FirstDayInWeek": 1,
            "StartDate": "2022-09-26T00:00:00+00:00",
            "EndDate": "2023-09-29T00:00:00+00:00"
        },
        "AllDays": [
            {
                "Name": "Monday",
                "DayOfWeek": 1,
                "IsDefault": True
            },
            {
                "Name": "Tuesday",
                "DayOfWeek": 2,
                "IsDefault": True
            },
            {
                "Name": "Wednesday",
                "DayOfWeek": 3,
                "IsDefault": True
            },
            {
                "Name": "Thursday",
                "DayOfWeek": 4,
                "IsDefault": True
            },
            {
                "Name": "Friday",
                "DayOfWeek": 5,
                "IsDefault": True
            },
            {
                "Name": "",
                "DayOfWeek": 6,
                "IsDefault": False
            },
            {
                "Name": "",
                "DayOfWeek": 0,
                "IsDefault": False
            }
        ]
    }

    week1_date = datetime(2022, 9, 26)
    until = datetime(2023, 6, 6)
    #this_week = datetime.now() - timedelta(datetime.now().weekday())
    view_weeks = []
    for i in range(weeks):
        this_week = datetime.now() - timedelta(datetime.now().weekday())
        this_week += timedelta(days = 7 * i)
        week_number = (this_week - week1_date).days / 7
        view_options["Weeks"].append({
                "WeekNumber": int(week_number),
                "WeekLabel": "Week 2",
                "FirstDayInWeek": this_week.isoformat() + "Z"
            })
    

    return view_options

def parse_date(date_str):
    '''
    Parses the date to a datetime date object
    '''
    year = int(date_str[:4])
    month = int(date_str[5:7])
    day = int(date_str[8:10])
    return datetime.datetime(year, month, day).date()

# FIXME: caching
# returns a list of module dictionary objects with the name, Identity and CategoryTypeIdentity
# or an error
def get_all_modules():
    modules = []
    for i in range(10):
        resp = requests.post(BASE_URL + f"Categories/Filter?pageNumber={i}", json=[], headers=HEADERS)
        if resp.status_code != 200:
            print(f"Failed to get modules: {resp.status_code}")
            print(resp.text)
            return resp.status_code
        resp = json.loads(resp.text)

        for m in resp["Results"]:
            modules.append({"name": m["Name"], "id": m["Identity"], "category": m["CategoryTypeIdentity"]})

        print(f"\n\nPage: {i}, total pages: {resp['TotalPages']}\n\n")
        if i > resp["TotalPages"]:
            break
    
    return modules

def module_search(module):
    mods = module.upper().split("_")
    query = mods[0]
    if mods[-1] in ["A", "B"]:
        query += f"_{mods[-1]}"
    print(f"Search for module: '{module}' with query '{query}'")
    resp = requests.post(BASE_URL + f"Categories/Filter?pageNumber=1&query={quote(query)}", json=[], headers=HEADERS)
    if resp.status_code != 200:
            print(f"Failed to get modules: {resp.status_code}")
            print(resp.text)
            return resp.status_code
    resp = resp.json()

    print(resp)

    m = resp["Results"][0]
    return {"name": m["Name"], "id": m["Identity"], "category": m["CategoryTypeIdentity"]}


def get_ical_for_modules(modules):
    print("Generating ics for modules: " + ", ".join(modules))
    ot_modules = []

    for m in modules:
        ot_mod = module_search(m)
        if not ot_mod:
            print("Couldn't find module: " + m)
            continue
        ot_modules.append(ot_mod)

    req_data = {"CategoryIdentities": [m["id"] for m in ot_modules], "ViewOptions": get_view_options()}
    print("Fetching events for modules:")
    print(req_data)
    events = requests.post(BASE_URL + "categories/events/filter", json=req_data, headers=HEADERS)
    if events.status_code != 200:
        print(events.status_code)
        print(events.text)
        return events.text

    print(events.text)

    timetable = events.json()
    ical = Calendar()
    for module in timetable:
        m = " ".join(module["Name"].split(" ")[:-1])
        for event in module["CategoryEvents"]:
            name = m + ": " + event["EventType"]
            if len(list(filter(lambda ev: ev.location == event["Location"]
                    and ev.name == name
                    and ev.begin == datetime.fromisoformat(event["StartDateTime"]), ical.events))) > 0:
                print("Duplicate event! " + name + " at " + event["StartDateTime"])
                continue
            if "CSC318_A/PC Lab/01/02" in event["Name"]:
                print("Ignoring friday lab")
                continue
            if "CSC368_CSCM68_A/PC Lab/01/02" in event["Name"]:
                print("Ignoring wednesday afternoon embedded lab")
                continue
            desc = event["Name"]
            if len(event["ExtraProperties"]) > 1:
                desc += " happens on weeks " + event["ExtraProperties"][1]["Value"]
            url = ""
            if len(event["ExtraProperties"]) > 2:
                url = event["ExtraProperties"][2]["Value"]
            ev = Event(name=name,
                description=desc,
                location=event["Location"],
                begin=datetime.fromisoformat(event["StartDateTime"]),
                end=datetime.fromisoformat(event["EndDateTime"]),
                url=url)
            ical.events.add(ev)

    return ical



