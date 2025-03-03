from flask import Flask, request, jsonify
import requests
from skyfield.api import load, EarthSatellite
from datetime import datetime, timezone
import numpy as np

app = Flask(__name__)

# URL to fetch TLE data (Update the group accordingly)
TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium-33-debris&FORMAT=tle"

# Load timescale
ts = load.timescale()

def fetch_tle(satellite_name):
    """Fetch TLE for a given satellite name."""
    response = requests.get(TLE_URL)
    if response.status_code != 200:
        return None, None

    lines = response.text.splitlines()
    for i in range(len(lines)):
        if satellite_name in lines[i]:
            return lines[i+1], lines[i+2]

    return None, None  # If satellite not found

def eci_to_ecef(x, y, z, gmst):
    """Convert ECI to ECEF using Greenwich Mean Sidereal Time (GMST)."""
    cos_theta = np.cos(gmst)
    sin_theta = np.sin(gmst)

    x_ecef = cos_theta * x + sin_theta * y
    y_ecef = -sin_theta * x + cos_theta * y
    z_ecef = z  # Z remains unchanged

    return x_ecef, y_ecef, z_ecef

def ecef_to_lla(x, y, z):
    """Convert ECEF to Latitude, Longitude, and Altitude using WGS84 model."""
    a = 6378.137  # Equatorial radius in km
    e = 8.1819190842622e-2  # Eccentricity

    b = np.sqrt(a**2 * (1 - e**2))
    ep = np.sqrt((a**2 - b**2) / b**2)
    p = np.sqrt(x**2 + y**2)
    theta = np.arctan2(z * a, p * b)

    lon = np.arctan2(y, x)
    lat = np.arctan2(z + ep**2 * b * np.sin(theta)**3, p - e**2 * a * np.cos(theta)**3)
    N = a / np.sqrt(1 - e**2 * np.sin(lat)**2)
    alt = p / np.cos(lat) - N

    # Convert radians to degrees
    lat = np.degrees(lat)
    lon = np.degrees(lon)

    return lat, lon, alt

@app.route('/satellite-position', methods=['GET'])
def get_satellite_position():
    """API endpoint to return satellite's Latitude, Longitude, and Altitude."""
    satellite_name = request.args.get('satellite')
    
    if not satellite_name:
        return jsonify({"error": "Missing satellite parameter"}), 400

    line1, line2 = fetch_tle(satellite_name)
    if not line1 or not line2:
        return jsonify({"error": "Satellite TLE data not found"}), 404

    satellite = EarthSatellite(line1, line2, satellite_name, ts)
    now = ts.now()

    # Compute ECI coordinates
    geocentric = satellite.at(now)
    x, y, z = geocentric.position.km

    # Convert ECI to ECEF
    gmst = now.gmst * (np.pi / 180)  # Convert degrees to radians
    x_ecef, y_ecef, z_ecef = eci_to_ecef(x, y, z, gmst)

    # Convert ECEF to LLA
    lat, lon, alt = ecef_to_lla(x_ecef, y_ecef, z_ecef)

    return jsonify({
        "satellite": satellite_name,
        "latitude": lat,
        "longitude": lon,
        "altitude_km": alt
    })

if __name__ == '__main__':
    app.run(debug=True)
