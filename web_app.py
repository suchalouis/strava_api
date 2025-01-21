# --- Import ---

import os
from flask import Flask, render_template, request, redirect, url_for
from strava_utils import Strava_Handler 

# --- Initialize Flask App ---
app = Flask(__name__)

# --- Strava API Credentials ---
CLIENT_ID = "145566"
CLIENT_SECRET = "d0949d11cf40903f77545b4646893c7876133585"

# --- Initialize Strava_Handler ---
strava = Strava_Handler(client_id=CLIENT_ID, client_secrets=CLIENT_SECRET)

# --- Web App Function ---

@app.route('/')
def home():
    """Home page with conditional display based on authentication status."""
    is_authenticated = strava.acces_token != ""
    return render_template('index.html', is_authenticated=is_authenticated)

@app.route('/connect')
def connect_to_strava():
    """Redirect the user to Strava's authorization page."""
    strava.get_authorization_url()
    return redirect(
        f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=activity:read_all"
    )

@app.route('/exchange_token')
def exchange_token():
    """Handle the redirect from Strava and exchange the authorization code for an access token."""
    auth_code = request.args.get('code')
    if not auth_code:
        return "Error: Authorization code not provided.", 400

    strava.set_auth(auth_code)

    if strava.acces_token:
        return redirect(url_for('map_view'))
    else:
        return "Error: Unable to fetch access token.", 400

@app.route('/activities')
def load_activities():
    """Display a list of Strava activities."""
    if not strava.acces_token:
        return redirect(url_for('home'))

    activities = strava.get_activities()
    return render_template('activities.html', activities=activities)

@app.route('/map')
def map_view():
    """Display a map of activities."""
    if not strava.acces_token:
        return redirect(url_for('home'))

    # Fetch activities and generate the map
    activities = strava.get_activities()
    activity_map = strava.activity_map(activities, save=True)

    # Return the generated map
    return render_template("activities_map.html")

if __name__ == "__main__":
    app.run(debug=True)
