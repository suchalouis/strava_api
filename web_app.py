from flask import Flask, render_template, request, redirect, url_for
import requests
import polyline
import folium
import os

# Strava API credentials
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRETS"
AUTH_URL = f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=activity:read_all"

# Initialize Flask app
app = Flask(__name__)

# Store access token globally
access_token = ""


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/connect')
def connect_to_strava():
    """Redirect the user to Strava's authorization page"""
    return redirect(AUTH_URL)


@app.route('/exchange_token')
def exchange_token():
    """Handle the redirect from Strava and exchange the authorization code for an access token"""
    global access_token

    # Extract the authorization code from the URL
    auth_code = request.args.get('code')

    # Prepare the request payload to exchange the code for an access token
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
    }

    # Request the access token
    response = requests.post(token_url, data=payload).json()

    # Save the access token
    access_token = response.get("access_token")

    if access_token:
        return redirect(url_for('map_view'))  # Redirect to the map view after successful authentication
    else:
        return "Error: Unable to fetch access token.", 400


@app.route('/activities')
def load_activities():
    """Display a list of Strava activities"""
    if not access_token:
        return redirect(url_for('home'))

    headers = {"Authorization": f"Bearer {access_token}"}
    activities_url = "https://www.strava.com/api/v3/activities"
    response = requests.get(activities_url, headers=headers).json()
    return render_template('activities.html', activities=response)


@app.route('/map')
def map_view():
    """Display the map of activities"""
    if not access_token:
        return redirect(url_for('home'))

    # Fetch activities and generate the map
    activities_url = "https://www.strava.com/api/v3/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(activities_url, headers=headers).json()

    # Create the map using the first activity
    latest_activity = response[0]
    coords = polyline.decode(latest_activity["map"]["summary_polyline"])
    activity_map = folium.Map(location=coords[0], zoom_start=13)

    # Add activities to the map
    for activity in response:
        polyline_data = activity["map"].get("summary_polyline")
        if polyline_data:
            coords = polyline.decode(polyline_data)
            tooltip = f'{activity["name"]}<br>Distance: {activity["distance"] / 1000:.2f} km'
            folium.PolyLine(coords, color="green", weight=2.5, tooltip=tooltip).add_to(activity_map)

    # Save and return the map as an HTML file
    map_file = "templates/activities_map.html"
    activity_map.save(map_file)
    return render_template("activities_map.html")


if __name__ == "__main__":
    app.run(debug=True)
