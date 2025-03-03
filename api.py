from flask import Flask, request, jsonify
import requests
from skyfield.api import load, EarthSatellite
from skyfield.toposlib import ITRSPosition
from datetime import datetime, timezone

app = Flask(__name__)

# Base URL for TLE data
TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium-33-debris&FORMAT=tle"

def fetch_tle(satellite_name):
    """Fetch TLE data from Celestrak."""
    response = requests.get(TLE_URL)
    if response.status_code != 200:
        raise ValueError("Failed to fetch TLE data")
    
    lines = response.text.split("\n")
    for i in range(len(lines)):
        if lines[i].strip() == satellite_name:
            return lines[i+1].strip(), lines[i+2].strip()
    
    raise ValueError("Satellite TLE data not found")

def get_satellite_position(satellite_name):
    """Compute satellite position (Lat, Lon, Alt)."""
    try:
        line1, line2 = fetch_tle(satellite_name)
        ts = load.timescale()
        satellite = EarthSatellite(line1, line2, satellite_name, ts)

        now = ts.now()
        geocentric = satellite.at(now)

        # Convert ECI (X, Y, Z) to Lat, Lon, Alt
        itrs_position = geocentric.frame_xyz_and_velocity(itrs=True)[0]
        lat, lon, alt = itrs_position.to_latlon()

        return {
            "satellite": satellite_name,
            "latitude": lat.degrees,
            "longitude": lon.degrees,
            "altitude_km": alt.km
        }
    except Exception as e:
        return {"error": str(e)}

@app.route("/")
def home():
    return "Welcome to the ML Space API! Use the `/satellite-position` endpoint."

@app.route("/satellite-position", methods=["GET"])
def satellite_position():
    """API endpoint to get satellite position."""
    satellite_name = request.args.get("satellite")
    if not satellite_name:
        return jsonify({"error": "Satellite name is required"}), 400
    
    result = get_satellite_position(satellite_name)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
