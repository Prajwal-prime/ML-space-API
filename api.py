from flask import Flask, request, jsonify
import requests
from skyfield.api import load, wgs84
from sgp4.api import Satrec

app = Flask(__name__)

# TLE Source
TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium-33-debris&FORMAT=tle"

@app.route("/")
def home():
    """Root endpoint to avoid 404 error."""
    return jsonify({"message": "Welcome to the ML Space API! Use the `/satellite-position` endpoint."})

def fetch_tle(satellite_name):
    """Fetches TLE data from Celestrak for a specific satellite."""
    response = requests.get(TLE_URL)
    if response.status_code != 200:
        return None, None

    lines = response.text.strip().split("\n")
    for i in range(len(lines) - 2):
        if satellite_name in lines[i]:
            return lines[i+1], lines[i+2]
    
    return None, None

def get_satellite_position(satellite_name):
    """Calculates the satellite's position in Lat, Lon, and Alt."""
    line1, line2 = fetch_tle(satellite_name)
    if not line1 or not line2:
        return None

    ts = load.timescale()
    t = ts.now()
    jd, fr = t.tt.jd1, t.tt.jd2



    satellite = Satrec.twoline2rv(line1, line2)
    e, r, v = satellite.sgp4(jd, fr)
    if e != 0:
        return None  

    geocentric = wgs84.xyz(r[0], r[1], r[2])
    subpoint = wgs84.subpoint(geocentric)

    return {
        "satellite": satellite_name,
        "latitude": subpoint.latitude.degrees,
        "longitude": subpoint.longitude.degrees,
        "altitude_km": subpoint.elevation.km
    }

@app.route("/satellite-position", methods=["GET"])
def satellite_position():
    """API endpoint to get satellite position."""
    satellite_name = request.args.get("satellite", "").strip()
    if not satellite_name:
        return jsonify({"error": "Satellite name is required"}), 400

    position = get_satellite_position(satellite_name)
    if not position:
        return jsonify({"error": "Satellite TLE data not found"}), 404

    return jsonify(position)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
