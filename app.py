#!/usr/bin/env python3
"""
Flask web application for Strava Activity Tracking
Provides OAuth2 authentication, activity visualization, and map integration.
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import requests
from datetime import datetime, timezone
import json
from typing import Dict, List, Optional
import pandas as pd
from config import get_config
from utils.strava_api import create_strava_client

app = Flask(__name__)

# Load configuration based on environment
config_class = get_config()
app.config.from_object(config_class)

# Validate configuration on startup
config_class.validate_config()

# In-memory cache for activities (simple implementation)
activities_cache = {}

# Create Strava client instance
strava_client = create_strava_client(app.config)


@app.route('/')
def index():
    """Main application page."""
    if not StravaOAuth.is_token_valid():
        return render_template('index.html', authenticated=False)
    
    return render_template('index.html', authenticated=True)


@app.route('/login')
def login():
    """Initiate Strava OAuth2 login."""
    auth_url = StravaOAuth.get_authorization_url()
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """Handle OAuth2 callback from Strava."""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        return f"Authentication error: {error}", 400
    
    if not code:
        return "No authorization code received", 400
    
    try:
        # Exchange code for tokens
        token_data = StravaOAuth.exchange_token(code)
        session['strava_token'] = token_data
        
        # Clear activities cache when new user logs in
        activities_cache.clear()
        
        return redirect(url_for('index'))
    
    except Exception as e:
        return f"Token exchange failed: {str(e)}", 500


@app.route('/logout')
def logout():
    """Logout user and clear session."""
    session.pop('strava_token', None)
    activities_cache.clear()
    return redirect(url_for('index'))


@app.route('/api/activities')
def api_activities():
    """API endpoint to get user's activities."""
    if not StravaOAuth.ensure_valid_token():
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        # Check cache first
        user_id = session['strava_token'].get('athlete', {}).get('id', 'unknown')
        cache_key = f"activities_{user_id}"
        
        if cache_key in activities_cache:
            return jsonify(activities_cache[cache_key])
        
        # Get current year activities
        current_year = datetime.now().year
        start_of_year = datetime(current_year, 1, 1, tzinfo=timezone.utc)
        
        activities = []
        page = 1
        per_page = 50
        
        while True:
            params = {
                'after': int(start_of_year.timestamp()),
                'per_page': per_page,
                'page': page
            }
            
            page_activities = make_strava_request('/athlete/activities', params)
            
            if not page_activities:
                break
            
            activities.extend(page_activities)
            page += 1
            
            # Limit to prevent excessive API calls
            if len(activities) >= 200:
                break
        
        # Process activities for frontend
        processed_activities = []
        for activity in activities:
            start_date = pd.to_datetime(activity.get('start_date_local', activity.get('start_date')))
            
            processed_activity = {
                'id': activity.get('id'),
                'name': activity.get('name', 'Sans nom'),
                'type': activity.get('type', 'Inconnu'),
                'sport_type': activity.get('sport_type', activity.get('type', 'Inconnu')),
                'date': start_date.strftime('%Y-%m-%d') if start_date else None,
                'distance_km': round(activity.get('distance', 0) / 1000, 2),
                'duration_minutes': round(activity.get('moving_time', 0) / 60, 1),
                'elevation_gain': activity.get('total_elevation_gain', 0),
                'average_speed': round(activity.get('average_speed', 0) * 3.6, 1),  # m/s to km/h
                'has_polyline': bool(activity.get('map', {}).get('summary_polyline')),
                'start_latlng': activity.get('start_latlng')
            }
            processed_activities.append(processed_activity)
        
        # Sort by date (most recent first)
        processed_activities.sort(key=lambda x: x['date'] or '', reverse=True)
        
        # Cache the results
        activities_cache[cache_key] = processed_activities
        
        return jsonify(processed_activities)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/activity/<int:activity_id>/polyline')
def api_activity_polyline(activity_id):
    """API endpoint to get activity polyline data."""
    if not StravaOAuth.ensure_valid_token():
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        # Get detailed activity data
        activity_detail = make_strava_request(f'/activities/{activity_id}')
        
        polyline_data = activity_detail.get('map', {}).get('summary_polyline')
        
        if not polyline_data:
            return jsonify({'error': 'No polyline data available'}), 404
        
        return jsonify({
            'polyline': polyline_data,
            'activity_id': activity_id,
            'name': activity_detail.get('name', 'Sans nom'),
            'type': activity_detail.get('type', 'Inconnu'),
            'start_latlng': activity_detail.get('start_latlng')
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """API endpoint to get activity statistics."""
    if not StravaOAuth.ensure_valid_token():
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        # Get activities from cache or API
        user_id = session['strava_token'].get('athlete', {}).get('id', 'unknown')
        cache_key = f"activities_{user_id}"
        
        if cache_key not in activities_cache:
            # Trigger activities fetch
            api_activities()
        
        activities = activities_cache.get(cache_key, [])
        
        if not activities:
            return jsonify({
                'total_activities': 0,
                'total_distance_km': 0,
                'total_time_hours': 0,
                'total_elevation_m': 0
            })
        
        # Calculate statistics
        total_activities = len(activities)
        total_distance = sum(a['distance_km'] for a in activities)
        total_time = sum(a['duration_minutes'] for a in activities) / 60  # Convert to hours
        total_elevation = sum(a['elevation_gain'] for a in activities)
        
        # Activity type breakdown
        type_counts = {}
        for activity in activities:
            activity_type = activity['type']
            type_counts[activity_type] = type_counts.get(activity_type, 0) + 1
        
        return jsonify({
            'total_activities': total_activities,
            'total_distance_km': round(total_distance, 1),
            'total_time_hours': round(total_time, 1),
            'total_elevation_m': round(total_elevation, 0),
            'activity_types': type_counts
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'], host=app.config['HOST'], port=app.config['PORT'])




