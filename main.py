from flask_cors import CORS
from flask import Flask, request, abort
import requests, re, csv
from ics import Calendar
from urllib.parse import urlparse, quote
from time import sleep
from opentimetable import *
from waitress import serve
import logging
import os

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

DOMAIN = "calebs.dev"
headers = {'User-Agent': 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
'Accept-Encoding': 'gzip, deflate, br',
'Accept-Language': 'en-US,en;q=0.9'}

@app.route("/", methods=['GET'])
def index():
    html = """
    <!DOCTYPE html>
<html>
<body>

<h2>MyTimetable to Open Timetable converter</h2>
<p>This form takes a link to a My Timetable iCal file which you can get by going to https://mytimetable.swansea.ac.uk<br>
and returns an equivalent link you can use which will fetch the data from Open Timetable instead, as apparently<br>
that's what we /have/ to use. The MyTimetable link is only used to figure out what modules you take, you should check<br>
that all of your modules are in the returned URL and add them manually if not - or if they don't match the format<br>
Open Timetable uses for them.</p>

<form action="/api/generate">
  <label for="ical">MyTimetable iCal link</label><br>
  <input type="text" id="ical" name="ical" value=""><br>
  <input type="submit" value="Submit">
</form> 

</body>
</html>

"""

    return html

# https://scientia-eu-v3-4-api-d1-04.azurewebsites.net/api/ical/c0fafdf7-2aab-419e-a69b-bbb9e957303c/141c474f-bd21-8c56-60fe-dbf755ebe241/timetable.ics
# mytimetable_ics should be everything after /api/ical/, e.g.
# c0fafdf7-2aab-419e-a69b-bbb9e957303c/141c474f-bd21-8c56-60fe-dbf755ebe241/timetable.ics
@app.route('/api/generate', methods=['GET'])
def generate():
    mytimetable_link = request.args.get('ical')
    print("Got link: " + mytimetable_link)
    url = ""
    try:
        url = f"https://scientia-eu-v3-4-api-d1-04.azurewebsites.net{urlparse(mytimetable_link).path}"
    except Exception as e:
        print("Failed to parse URL!")
        return f"Invalid URL: \"{mytimetable_link}\""
    print(f"Requesting timetable: {url}")

    resp = 0
    for i in range(5):
        timetable = requests.get(url, headers=headers)
        if timetable.status_code == 200:
            break
        print(timetable.text)
        sleep(0.5)

    if timetable.status_code != 200:
        return f"Failed to get timetable: {timetable.status_code}"

    print(timetable.text)
    c = Calendar(timetable.text)

    print(request.form)

    modules = []
    for ev in c.events:
        m = ev.name.split("/")[0].upper()
        if m not in modules:
            modules.append(m)

    data = quote(';'.join(modules))

    return(f"{request.url_root}api/ics?modules={data}")

@app.route('/api/ics', methods=['GET'])
def ics():
    modules = request.args.get("modules")

    return get_ical_for_modules(modules.split(";")).serialize()


# Disable caching
@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=5000, url_scheme=os.environ.get('URL_SCHEME') or 'http')
