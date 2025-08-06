import requests
from flask import session
from typing import List, Dict

class StravaAPIClient:
    """
    Client for interacting with Strava API using OAuth2 with Flask session storage.
    """
    BASE_URL = "https://www.strava.com/api/v3"
    AUTH_URL = "https://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/oauth/token"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, scopes: List[str] = None) -> str:
        if scopes is None:
            scopes = ["read", "activity:read_all"]
        scope_string = ",".join(scopes)
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope_string,
            "approval_prompt": "auto"
        }
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.AUTH_URL}?{param_string}"

    def exchange_token(self, authorization_code: str) -> Dict:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": authorization_code,
            "grant_type": "authorization_code"
        }
        response = requests.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        tokens = response.json()
        session['strava_token'] = tokens
        return tokens

    def refresh_token(self) -> Dict:
        refresh_token = session['strava_token'].get('refresh_token')
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        response = requests.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        tokens = response.json()
        session['strava_token'] = tokens
        return tokens

    def get_activities(self) -> List[Dict]:
        access_token = session['strava_token'].get('access_token')
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(f"{self.BASE_URL}/athlete/activities", headers=headers)
        response.raise_for_status()
        return response.json()

    def calculate_statistics(self, activities: List[Dict]) -> Dict:
        total_distance = sum(activity.get('distance', 0) for activity in activities)
        total_time = sum(activity.get('moving_time', 0) for activity in activities)
        total_elevation = sum(activity.get('total_elevation_gain', 0) for activity in activities)
        return {
            "total_distance": total_distance,
            "total_time": total_time,
            "total_elevation": total_elevation
        }

def create_strava_client(app_config) -> StravaAPIClient:
    return StravaAPIClient(
        client_id=app_config['STRAVA_CLIENT_ID'],
        client_secret=app_config['STRAVA_CLIENT_SECRET'],
        redirect_uri=app_config['STRAVA_REDIRECT_URI']
    )
#!/usr/bin/env python3
"""
Strava API Client for Web Application
Refactored from strava_parser.py for Flask web usage with session-based token storage.
"""

import requests
import pandas as pd
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from flask import session


class StravaAPIClient:
    """Client for interacting with Strava API using OAuth2 with Flask session storage."""
    
    # Strava API URLs
    BASE_URL = "https://www.strava.com/api/v3"
    AUTH_URL = "https://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/oauth/token"
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize the Strava client for web usage.
        
        Args:
            client_id: Strava application client ID
            client_secret: Strava application client secret
            redirect_uri: OAuth2 redirect URI
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    def get_authorization_url(self, scopes: List[str] = None) -> str:
        """
        Generate OAuth2 authorization URL.
        
        Args:
            scopes: List of requested permissions (default: read,activity:read_all)
        
        Returns:
            Strava authorization URL
        """
        if scopes is None:
            scopes = ["read", "activity:read_all"]
        
        scope_string = ",".join(scopes)
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope_string,
            "approval_prompt": "auto"
        }
        
        # Build URL with parameters
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{self.AUTH_URL}?{param_string}"
        
        return auth_url
    
    def exchange_token(self, authorization_code: str) -> Dict:
        """
        Exchange authorization code for access tokens and store in session.
        
        Args:
            authorization_code: Authorization code received after authentication
        
        Returns:
            Dictionary containing tokens and expiration information
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": authorization_code,
            "grant_type": "authorization_code"
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Store tokens in Flask session
        session['strava_token'] = {
            'access_token': token_data["access_token"],
            'refresh_token': token_data["refresh_token"],
            'expires_at': token_data["expires_at"],
            'athlete': token_data.get("athlete", {})
        }
        
        return token_data
    
    def refresh_access_token(self) -> Dict:
        """
        Refresh expired access token using refresh token from session.
        
        Returns:
            Dictionary containing new tokens
        """
        if 'strava_token' not in session or 'refresh_token' not in session['strava_token']:
            raise ValueError("No refresh token available in session")
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": session['strava_token']['refresh_token']
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Update tokens in session
        session['strava_token'].update({
            'access_token': token_data["access_token"],
            'refresh_token': token_data["refresh_token"],
            'expires_at': token_data["expires_at"]
        })
        
        return token_data
    
    def is_token_valid(self) -> bool:
        """
        Check if current session token is valid.
        
        Returns:
            True if token is valid and not expired
        """
        if 'strava_token' not in session:
            return False
        
        token_data = session['strava_token']
        expires_at = token_data.get('expires_at', 0)
        
        return datetime.now().timestamp() < expires_at
    
    def ensure_valid_token(self) -> bool:
        """
        Ensure we have a valid token, refresh if necessary.
        
        Returns:
            True if token is valid, False if authentication is required
        """
        if not self.is_token_valid():
            if 'strava_token' in session and 'refresh_token' in session['strava_token']:
                try:
                    self.refresh_access_token()
                    return True
                except:
                    # Clear invalid session data
                    session.pop('strava_token', None)
                    return False
            return False
        return True
    
    def _make_authenticated_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make authenticated request to Strava API.
        
        Args:
            endpoint: API endpoint (e.g., "/athlete")
            params: Request parameters
        
        Returns:
            JSON response from API
        """
        if not self.ensure_valid_token():
            raise ValueError("Invalid or expired token. Re-authentication required.")
        
        headers = {
            "Authorization": f"Bearer {session['strava_token']['access_token']}",
            "Accept": "application/json"
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_athlete_info(self) -> Dict:
        """
        Get information about the authenticated athlete.
        
        Returns:
            Dictionary containing athlete information
        """
        return self._make_authenticated_request("/athlete")
    
    def get_activities(self, after: Optional[datetime] = None, 
                      before: Optional[datetime] = None, 
                      per_page: int = 50) -> List[Dict]:
        """
        Get athlete's activities.
        
        Args:
            after: Start date (inclusive)
            before: End date (exclusive)
            per_page: Number of activities per page (max 200)
        
        Returns:
            List of activities
        """
        activities = []
        page = 1
        
        while True:
            params = {
                "per_page": min(per_page, 200),  # API limit: 200
                "page": page
            }
            
            if after:
                params["after"] = int(after.timestamp())
            if before:
                params["before"] = int(before.timestamp())
            
            page_activities = self._make_authenticated_request("/athlete/activities", params)
            
            if not page_activities:
                break
                
            activities.extend(page_activities)
            page += 1
            
            # Pause to respect API limits
            time.sleep(0.1)
            
            # Limit to prevent excessive API calls in web context
            if len(activities) >= 200:
                break
        
        return activities
    
    def get_current_year_activities(self) -> List[Dict]:
        """
        Get all activities for the current year.
        
        Returns:
            List of current year activities
        """
        current_year = datetime.now().year
        start_of_year = datetime(current_year, 1, 1, tzinfo=timezone.utc)
        end_of_year = datetime(current_year + 1, 1, 1, tzinfo=timezone.utc)
        
        return self.get_activities(after=start_of_year, before=end_of_year)
    
    def get_activity_detail(self, activity_id: int) -> Dict:
        """
        Get detailed information about a specific activity including polyline data.
        
        Args:
            activity_id: ID of the activity to retrieve
        
        Returns:
            Dictionary containing detailed activity information including summary_polyline
        """
        return self._make_authenticated_request(f"/activities/{activity_id}")
    
    def activities_to_dataframe(self, activities: List[Dict]) -> pd.DataFrame:
        """
        Convert activities list to pandas DataFrame.
        
        Args:
            activities: List of activities from Strava API
        
        Returns:
            pandas DataFrame with activity data
        """
        if not activities:
            return pd.DataFrame()
        
        # Extract important data
        data = []
        for activity in activities:
            # Process date
            start_date = pd.to_datetime(activity.get('start_date_local', activity.get('start_date')))
            
            # Calculate average speed (m/s to km/h)
            distance_m = activity.get('distance', 0)
            moving_time_s = activity.get('moving_time', 1)  # Avoid division by zero
            avg_speed_kmh = (distance_m / 1000) / (moving_time_s / 3600) if moving_time_s > 0 else 0
            
            # Build record
            record = {
                'id': activity.get('id'),
                'date': start_date.date() if start_date else None,
                'name': activity.get('name', 'Sans nom'),
                'type': activity.get('type', 'Inconnu'),
                'sport_type': activity.get('sport_type', activity.get('type', 'Inconnu')),
                'distance_km': round(distance_m / 1000, 2) if distance_m else 0,
                'duration_minutes': round(moving_time_s / 60, 1) if moving_time_s else 0,
                'average_speed_kmh': round(avg_speed_kmh, 1),
                'elevation_gain_m': activity.get('total_elevation_gain', 0),
                'kudos_count': activity.get('kudos_count', 0),
                'calories': activity.get('calories'),
                'average_heartrate': activity.get('average_heartrate'),
                'max_heartrate': activity.get('max_heartrate'),
                'commute': activity.get('commute', False),
                'trainer': activity.get('trainer', False),
                'start_latitude': activity.get('start_latlng')[0] if activity.get('start_latlng') else None,
                'start_longitude': activity.get('start_latlng')[1] if activity.get('start_latlng') else None,
                'has_polyline': bool(activity.get('map', {}).get('summary_polyline'))
            }
            data.append(record)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Optimize data types
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df['commute'] = df['commute'].astype(bool)
            df['trainer'] = df['trainer'].astype(bool)
            df['has_polyline'] = df['has_polyline'].astype(bool)
        
        return df
    
    def get_activity_polyline(self, activity_id: int) -> Optional[str]:
        """
        Get the summary polyline for a specific activity.
        
        Args:
            activity_id: ID of the activity
        
        Returns:
            Encoded polyline string or None if not available
        """
        try:
            activity_detail = self.get_activity_detail(activity_id)
            return activity_detail.get('map', {}).get('summary_polyline')
        except:
            return None
    
    def calculate_activity_stats(self, activities: List[Dict]) -> Dict:
        """
        Calculate statistics from a list of activities.
        
        Args:
            activities: List of activities
        
        Returns:
            Dictionary containing calculated statistics
        """
        if not activities:
            return {
                'total_activities': 0,
                'total_distance_km': 0,
                'total_time_hours': 0,
                'total_elevation_m': 0,
                'activity_types': {}
            }
        
        total_activities = len(activities)
        total_distance = sum(activity.get('distance', 0) for activity in activities) / 1000  # Convert to km
        total_time = sum(activity.get('moving_time', 0) for activity in activities) / 3600  # Convert to hours
        total_elevation = sum(activity.get('total_elevation_gain', 0) for activity in activities)
        
        # Activity type breakdown
        type_counts = {}
        for activity in activities:
            activity_type = activity.get('type', 'Unknown')
            type_counts[activity_type] = type_counts.get(activity_type, 0) + 1
        
        return {
            'total_activities': total_activities,
            'total_distance_km': round(total_distance, 1),
            'total_time_hours': round(total_time, 1),
            'total_elevation_m': round(total_elevation, 0),
            'activity_types': type_counts
        }


def create_strava_client(app_config) -> StravaAPIClient:
    """
    Factory function to create a StravaAPIClient instance from Flask app config.
    
    Args:
        app_config: Flask application configuration (can be config class or dict)
    
    Returns:
        Configured StravaAPIClient instance
    """
    # Handle both config class and dict access
    if hasattr(app_config, 'STRAVA_CLIENT_ID'):
        # Config class
        return StravaAPIClient(
            client_id=app_config.STRAVA_CLIENT_ID,
            client_secret=app_config.STRAVA_CLIENT_SECRET,
            redirect_uri=app_config.STRAVA_REDIRECT_URI
        )
    else:
        # Dict-like access
        return StravaAPIClient(
            client_id=app_config['STRAVA_CLIENT_ID'],
            client_secret=app_config['STRAVA_CLIENT_SECRET'],
            redirect_uri=app_config['STRAVA_REDIRECT_URI']
        )


