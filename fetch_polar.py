#!/usr/bin/env python3
"""
Polar AccessLink API - OAuth2 Login and List Exercises

Before running:
1. Register your app at https://admin.polaraccesslink.com/
2. Export environment variables:
   export POLAR_CLIENT_ID=your_client_id
   export POLAR_CLIENT_SECRET=your_client_secret
   export POLAR_MEMBER_ID=my_user_123
3. Install: pip install requests
"""

import base64
import os
import sys
import webbrowser
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

with open('my.env', 'r') as fh:
    vars_dict = dict(
        tuple(line.replace('\n', '').split('='))
        for line in fh.readlines() if not line.startswith('#')
    )
os.environ.update(vars_dict)

CLIENT_ID = os.getenv("POLAR_CLIENT_ID")
CLIENT_SECRET = os.getenv("POLAR_CLIENT_SECRET")
MEMBER_ID = os.getenv("POLAR_MEMBER_ID", "my_user_123")
REDIRECT_URI = os.getenv("POLAR_REDIRECT_URI", "http://localhost:8080/callback")

AUTH_URL = "https://flow.polar.com/oauth2/authorization"
TOKEN_URL = "https://polarremote.com/v2/oauth2/token"
API_BASE = "https://www.polaraccesslink.com/v3"

auth_code = None
server = None

session = requests.Session()
session.headers.update({'Accept': 'application/json'})

def main():
    global server

    check_credentials()

    # Step 1: Start local server for OAuth callback
    server = HTTPServer(('localhost', 8080), CallbackHandler)
    print(f"Starting local server on port 8080...")

    # Step 2: Open browser for authorization
    auth_params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': 'accesslink.read_all'
    }
    auth_request_url = f"{AUTH_URL}?{'&'.join(f'{k}={v}' for k, v in auth_params.items())}"

    print(f"\nPlease authorize the application:")
    print(f"URL: {auth_request_url}\n")
    webbrowser.open(auth_request_url)

    # Step 3: Wait for authorization code
    server.handle_request()
    server.server_close()

    if not auth_code:
        print("Error: No authorization code received")
        sys.exit(1)

    print(f"\nAuthorization code received: {auth_code[:10]}...")

    # Step 4: Exchange code for access token
    try:
        token_data = get_access_token(auth_code)
        access_token = token_data['access_token']
        user_id = token_data.get('x_user_id', 'unknown')
        print(f"\nAccess token received for user: {user_id}")
        print(f"Token expires in: {token_data.get('expires_in', 'N/A')} seconds")
    except Exception as e:
        print(f"Error getting access token: {e}")
        sys.exit(1)

    session.headers.update({'Authorization': f'Bearer {access_token}'})

    # Step 5: Register user
    if not register_user():
        print("Failed to register user")
        sys.exit(1)

    # Step 6: List exercises
    try:
        exercises = list_exercises()
        print(f"\n{'='*60}")
        print(f"YOUR EXERCISES ({len(exercises)})")
        print(f"{'='*60}")

        if not exercises:
            print("No exercises found (only last 30 days are returned, and only ones after user registration).")

        for i, exercise in enumerate(exercises, 1):
            print(f"\n{i}. {exercise.get('id', 'N/A')}")
            print(f"   Sport: {exercise.get('sport', 'N/A')}")
            print(f"   Start: {exercise.get('start_time', 'N/A')}")
            print(f"   Duration: {exercise.get('duration', 'N/A')}")
            print(f"   Distance: {exercise.get('distance', 0)}m")
            print(f"   Calories: {exercise.get('calories', 0)}")
            print(f"   Heart Rate: Avg {exercise.get('heart_rate', {}).get('average', 'N/A')}, Max {exercise.get('heart_rate', {}).get('maximum', 'N/A')}")

            download_exercise(exercise)

        print(f"\n{'='*60}")
    except requests.exceptions.HTTPError as e:
        print(f"Error listing exercises: {e}")
        if hasattr(e, 'response') and e.response.status_code == 403:
            print("Hint: User may not have accepted all mandatory consents at https://account.polar.com")

    print("Refreshing database index...")
    from db import reindex
    reindex()

def download_exercise(exercise):
    """Download exercise data in TCX format"""
    start_time = exercise.get('start_time', '')
    # Parse ISO 8601 datetime and format as YYYY-MM-DD_HH-MM-SS
    if start_time:
        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        date_str = dt.strftime('%Y-%m-%d_%H-%M-%S')
    else:
        date_str = exercise.get('id', 'unknown')
    sp = exercise.get('sport', 'unknown').lower()
    filename = f"data/{date_str}_{sp}.tcx"
    if os.path.exists(filename):
        print(f"Exercise {exercise.get('id', '?')} already exists as {filename}, skipping download")
        return
    response = session.get(f"{API_BASE}/exercises/{exercise['id']}/tcx", headers={'Accept': 'application/vnd.garmin.tcx+xml'})
    if response.status_code == 404:
        print(f"TCX data not available for {exercise.get('id', '?')}, skipping download")
        return
    response.raise_for_status()
    with open(filename, 'wb') as f:
        f.write(response.content)
    print(f"Downloaded as {filename}")

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code, server
        query = parse_qs(urlparse(self.path).query)
        if 'code' in query:
            auth_code = query['code'][0]
            self.wfile.write(b"Authorization successful! You may close this window and return to the script.")
            self.send_response(200)
        else:
            self.wfile.write(b"Error: No authorization code received")
            self.send_response(400)

    def log_message(self, format, *args):
        return  # Suppress logs


def get_access_token(code):
    """Exchange authorization code for access token"""
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    base64_auth = base64.b64encode(auth_bytes).decode('ascii')

    headers = {
        'Authorization': f'Basic {base64_auth}',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()
    return response.json()


def register_user():
    """Register user to access their data"""

    response = session.post(f"{API_BASE}/users", json={"member-id": MEMBER_ID})

    if response.status_code == 200:
        print(f"User registered: {response.json()}")
    elif response.status_code == 409:
        print("User already registered")
    else:
        print(f"User registration error: {response.status_code} - {response.text}")
    return response.status_code in (200, 409)


def list_exercises():
    """List user's exercises"""
    response = session.get(f"{API_BASE}/exercises")
    response.raise_for_status()
    exercises = response.json()
    return exercises

def check_credentials():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: POLAR_CLIENT_ID and POLAR_CLIENT_SECRET environment variables are required")
        print("Set them with:")
        print("  export POLAR_CLIENT_ID=your_client_id")
        print("  export POLAR_CLIENT_SECRET=your_client_secret")
        sys.exit(1)

if __name__ == "__main__":
    main()
