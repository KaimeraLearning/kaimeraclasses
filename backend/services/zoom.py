"""Zoom API integration - Server-to-Server OAuth for meeting creation + SDK signature generation"""
import os
import time
import base64
import logging
import requests
import jwt

logger = logging.getLogger(__name__)

_token_cache = {"token": None, "expires_at": 0}


def _get_credentials():
    """Lazy-load Server-to-Server OAuth credentials for meeting creation"""
    return (
        os.environ.get("ZOOM_ACCOUNT_ID", ""),
        os.environ.get("ZOOM_CLIENT_ID", ""),
        os.environ.get("ZOOM_CLIENT_SECRET", "")
    )


def _get_sdk_credentials():
    """Lazy-load Meeting SDK credentials for embedded view"""
    return (
        os.environ.get("ZOOM_SDK_KEY", ""),
        os.environ.get("ZOOM_SDK_SECRET", "")
    )


def get_zoom_access_token():
    """Get Server-to-Server OAuth access token (cached for 50 min)"""
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now:
        return _token_cache["token"]

    account_id, client_id, client_secret = _get_credentials()
    if not client_id or not client_secret or not account_id:
        raise Exception("Zoom credentials not configured. Check ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET in .env")

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        "https://zoom.us/oauth/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={
            "grant_type": "account_credentials",
            "account_id": account_id
        },
        timeout=10
    )
    if resp.status_code != 200:
        logger.error(f"Zoom token error: {resp.status_code} {resp.text}")
        raise Exception(f"Failed to get Zoom access token: {resp.text}")

    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600) - 300
    return data["access_token"]


def create_zoom_meeting(topic: str, duration: int = 60, start_time: str = None):
    """Create a Zoom meeting and return meeting details"""
    token = get_zoom_access_token()

    meeting_data = {
        "topic": topic,
        "type": 2,
        "duration": duration,
        "timezone": "Asia/Kolkata",
        "settings": {
            "host_video": True,
            "participant_video": True,
            "join_before_host": True,
            "mute_upon_entry": False,
            "waiting_room": False,
            "auto_recording": "none"
        }
    }
    if start_time:
        meeting_data["start_time"] = start_time

    resp = requests.post(
        "https://api.zoom.us/v2/users/me/meetings",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=meeting_data,
        timeout=10
    )
    if resp.status_code not in (200, 201):
        logger.error(f"Zoom create meeting error: {resp.status_code} {resp.text}")
        raise Exception(f"Failed to create Zoom meeting: {resp.text}")

    return resp.json()


def generate_zoom_sdk_signature(meeting_number: int, role: int):
    """Generate JWT signature for Zoom Meeting SDK (role: 0=participant, 1=host)"""
    sdk_key, sdk_secret = _get_sdk_credentials()
    if not sdk_key or not sdk_secret:
        raise Exception("Zoom Meeting SDK credentials not configured (ZOOM_SDK_KEY, ZOOM_SDK_SECRET)")

    iat = int(time.time())
    exp = iat + 60 * 60 * 2

    payload = {
        "sdkKey": sdk_key,
        "appKey": sdk_key,
        "mn": meeting_number,
        "role": role,
        "iat": iat,
        "exp": exp,
        "tokenExp": exp
    }

    signature = jwt.encode(payload, sdk_secret, algorithm="HS256")
    return signature
