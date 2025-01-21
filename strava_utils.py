# ---- Import ----

import urllib3
import requests
import folium
import polyline

from dataclasses import dataclass
from typing import List, Dict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---- Variables ----

client_id = "YOUR_CLIENT_ID"
client_secrets = "YOUR_CLIENT_SECRETS"

# ---- Classes ----

@dataclass
class Strava_Handler():
    def __init__(
            self, 
            client_id: int, 
            client_secrets: str
        ):

        self.client_id = client_id
        self.client_secrets = client_secrets
        self.token = ""
        self.refresh_token = ""
        self.payload = {}
        self.auth_code=""
        self.acces_token=""

    def get_authorization_url(self):
        auth_url = f"https://www.strava.com/oauth/authorize?client_id={self.client_id}&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=activity:read_all"
        print("Go to the following URL and authorize the app:")
        print(auth_url)
        # auth_code = input("Enter the authorization code here: ")
        # return auth_code
    
    def set_payload(self):
        self.payload={
            'client_id': client_id,
            'client_secret': client_secrets,
            'code': self.auth_code,
            'grant_type': "authorization_code",
            'f': 'json'
        }

    def set_auth(self, auth_code):
        self.auth_code = auth_code
        self.set_payload()
        strava_auth=requests.post(
            url=u"https://www.strava.com/api/v3/oauth/token", 
            data=self.payload, 
            verify=False
        ).json()
        if strava_auth.get("refresh_token"):
            self.refresh_token=strava_auth.get("refresh_token")
            self.acces_token=strava_auth.get("access_token")
            print("Tokens found !")
        else:
            print("No token found !")
    
    def get_activities(self, last: int = 30):
        url = 'https://www.strava.com/api/v3/activities'
        headers = {
            'Authorization': f"Bearer {self.acces_token}"
        }
        response = requests.get(url, headers=headers).json()
        return response[:last]
    
    def activity_map(self, activities:List[Dict] = [], save:bool=False):

        if activities:
            latest_activity = activities[0]
            center_coord = polyline.decode(latest_activity.get("map").get("summary_polyline"))[0]

            base_map = folium.Map(location=center_coord, zoom_start=13)

            for activity in activities:
                coords = polyline.decode(activity.get("map").get("summary_polyline"))
                if coords:
                    tooltip = f'{activity.get("name")}<br>Date: {activity.get("start_date_local")}<br>Distance: {activity.get("distance") / 1000:.2f} km'
                    folium.PolyLine(coords, color="blue", weight=2.5, opacity=1, tooltip=tooltip).add_to(base_map)

            if save:
                base_map.save("activities_map.html")
            return base_map