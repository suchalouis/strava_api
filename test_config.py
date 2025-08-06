#!/usr/bin/env python3
"""
Test script to verify configuration management is working properly.
"""

try:
    from config import get_config
    
    print("Testing configuration management...")
    
    # Get configuration
    config = get_config()
    print("✅ Configuration loaded successfully")
    
    # Test configuration values
    print(f"CLIENT_ID: {config.STRAVA_CLIENT_ID}")
    print(f"SECRET_KEY set: {bool(config.SECRET_KEY)}")
    print(f"REDIRECT_URI: {config.STRAVA_REDIRECT_URI}")
    print(f"DEBUG mode: {config.DEBUG}")
    print(f"HOST: {config.HOST}")
    print(f"PORT: {config.PORT}")
    
    # Validate configuration
    config.validate_config()
    print("✅ Configuration validation passed")
    
    print("\n🎉 Configuration management is working correctly!")
    
except Exception as e:
    print(f"❌ Configuration test failed: {e}")
    import traceback
    traceback.print_exc()
