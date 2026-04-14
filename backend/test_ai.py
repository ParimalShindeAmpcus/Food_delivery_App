#!/usr/bin/env python3
"""
Test script for Groq AI integration in Foodie Feed backend.
Run this to verify AI endpoints work with your Groq API key.
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_ai_endpoints():
    """Test all AI endpoints with sample data."""

    base_url = "http://localhost:4000"

    # Test data
    test_query = "cheap veg pizza under 200"
    test_history = [
        {
            "items": [
                {
                    "menuItem": {
                        "name": "Margherita Pizza",
                        "price": 12.99,
                        "isVeg": True
                    },
                    "quantity": 1
                }
            ],
            "total": 12.99
        }
    ]

    print("Testing Groq AI endpoints...")

    # Test restaurants endpoint
    try:
        print("\n0. Testing restaurants endpoint...")
        response = requests.get(f"{base_url}/api/restaurants")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Restaurants endpoint works: {len(result)} restaurants")
            if result:
                print(f"First restaurant image: {result[0].get('image', 'No image')}")
        else:
            print(f"❌ Restaurants failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Restaurants error: {e}")

    # Test search parsing
    try:
        print("\n1. Testing search parsing...")
        response = requests.post(f"{base_url}/api/ai/search", json={"query": test_query})
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Search parsing works: {result}")
        else:
            print(f"❌ Search parsing failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Search parsing error: {e}")

    # Test intent detection
    try:
        print("\n2. Testing intent detection...")
        response = requests.post(f"{base_url}/api/ai/intent", json={"query": test_query})
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Intent detection works: {result}")
        else:
            print(f"❌ Intent detection failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Intent detection error: {e}")

    # Test recommendations
    try:
        print("\n3. Testing recommendations...")
        response = requests.post(f"{base_url}/api/ai/recommend", json={"history": test_history})
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Recommendations work: {result}")
        else:
            print(f"❌ Recommendations failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Recommendations error: {e}")

    # Test chat
    try:
        print("\n4. Testing chat response...")
        response = requests.post(f"{base_url}/api/ai/chat", json={"query": test_query})
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Chat works: {result}")
        else:
            print(f"❌ Chat failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Chat error: {e}")

    print("\nTest complete!")

if __name__ == "__main__":
    # Check if API key is set
    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not found in environment variables!")
        print("Please set your Groq API key in the .env file")
        print("Get it from: https://console.groq.com/keys")
        exit(1)

    # Check if backend is running
    try:
        response = requests.get("http://localhost:4000/api/health")
        if response.status_code != 200:
            print("❌ Backend is not running! Start it with:")
            print("python -m uvicorn main:app --host 0.0.0.0 --port 4000 --reload")
            exit(1)
    except:
        print("❌ Cannot connect to backend! Make sure it's running on port 4000")
        exit(1)

    test_ai_endpoints()
