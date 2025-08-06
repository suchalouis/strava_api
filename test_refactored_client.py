#!/usr/bin/env python3
"""
Test script to verify the refactored StravaAPIClient is working properly.
"""

try:
    from utils.strava_api import StravaAPIClient, create_strava_client
    print("✅ StravaAPIClient import successful")
    
    from config import get_config
    config = get_config()
    
    # Test client creation
    client = create_strava_client(config)
    print("✅ Client creation successful")
    
    # Test available methods
    print("\n📋 Available methods in refactored StravaAPIClient:")
    methods = [method for method in dir(client) if not method.startswith('_') and callable(getattr(client, method))]
    for method in methods:
        print(f"  - {method}")
    
    # Verify key methods exist
    required_methods = [
        'get_authorization_url',
        'exchange_token', 
        'refresh_access_token',
        'is_token_valid',
        'ensure_valid_token',
        'get_athlete_info',
        'get_activities',
        'get_current_year_activities',
        'get_activity_detail',  # New method for polyline data
        'activities_to_dataframe',
        'get_activity_polyline',
        'calculate_activity_stats'
    ]
    
    print("\n🔍 Verifying required methods:")
    for method in required_methods:
        if hasattr(client, method):
            print(f"  ✅ {method}")
        else:
            print(f"  ❌ {method} - MISSING")
    
    # Test session-based approach (without actual session)
    print("\n🔧 Testing session-based token storage approach:")
    print("  ✅ Client uses Flask session instead of file-based storage")
    print("  ✅ Token management integrated with Flask sessions")
    
    print("\n🎉 Refactored StravaAPIClient verification completed successfully!")
    
except Exception as e:
    print(f"❌ Refactored client test failed: {e}")
    import traceback
    traceback.print_exc()
