from gpiozero import RGBLED, Button, LED
from escpos.printer import Usb
from PIL import Image
import requests
import os
import json
import asyncio
import socket
from time import sleep, time
import sqlite3
import sseclient
from io import BytesIO

messages = []
mode = "initializing"
authenticated = False
isActive = True

# Refresh a token this many seconds *before* it actually expires, so we
# never send a request with an access token that dies mid-flight.
TOKEN_REFRESH_MARGIN = 30


def load_dotenv_file(path='.env'):
    if not os.path.exists(path):
        return
    with open(path, 'r', encoding='utf-8') as dotenv_file:
        for raw_line in dotenv_file:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv_file()

p = Usb(0x0416, 0x5011, 0)
sysLed = LED(23);
button = Button(2)

# server credentials
host = os.environ.get("HOST")
username = os.environ.get("USERNAME")
password = os.environ.get("PASSWORD")


class AuthenticationError(Exception):
    """Raised when we cannot get a usable access token (login + refresh both failed)."""
    pass



def check_printer():
    """
    Returns True when printer responds.
    """
    global mode
    try:
        p._raw(b'\x1D\x61\x01')
        return True
    except Exception as e:
        print(f"Printer check failed: {e}")
        mode = "no_printer"
        return False


def check_internet_connection():
    """
    Returns True when internet is available.
    """
    global mode
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=3)
        return True
    except OSError:
        print("No internet connection")
        mode = "no_internet"
        return False


def check_paper_status():
    """
    ESC/POS paper detection.
    Note: not every printer supports this.
    """
    global mode
    try:
        status = p._raw(b'\x10\x04\x04')  # DLE EOT paper status

        # Depends on printer model.
        # Many printers return a byte where bit 3 indicates paper end.
        if status and status[0] & 0b00001000:
            print("Printer is out of paper")
            mode = "no_paper"
            return False

        return True

    except Exception as e:
        print(f"Paper status check failed: {e}")
        return False


def wait_for_system_ready():
    global mode
    mode = "checking_system_status"

    checks = {
        "Printer": check_printer,
        "Internet": check_internet_connection,
        "Paper": check_paper_status,
    }

    while True:
        failed = []

        for name, check in checks.items():
            if not check():
                failed.append(name)

        if not failed:
            print("System ready")
            mode = "ready"
            return True

        print("Waiting for:", ", ".join(failed))


        sleep(10)


def intitialize_db():
    global mode
    mode = "initializing_DB"
    conn = sqlite3.connect('appdata.db')

    cursor = conn.cursor()

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS device_settings
                    (id INTEGER PRIMARY KEY, setting_key TEXT UNIQUE, setting_value TEXT)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS wifi_networks
                    (id INTEGER PRIMARY KEY, ssid TEXT UNIQUE, password TEXT, protocol TEXT, connected INTEGER DEFAULT 0)"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS server_auth
                    (id INTEGER PRIMARY KEY, access_token TEXT, refresh_token TEXT, token_expiry TEXT)"""
    )
    conn.commit()
    conn.close()


def load_print_image(image_source, max_width=400):
    if image_source.startswith("http://") or image_source.startswith("https://"):
        response = requests.get(image_source, timeout=10)
        response.raise_for_status()
        image_data = BytesIO(response.content)
        image = Image.open(image_data)
    else:
        image = Image.open(image_source)

    image = image.convert("P")
    if image.width > max_width:
        new_height = round(image.height * max_width / image.width)
        image = image.resize((max_width, new_height), Image.LANCZOS)
    return image


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
# Design:
#   - store_tokens()/clear_tokens() are the only things that touch the
#     server_auth table.
#   - sign_in() does a fresh username/password login.
#   - perform_login() wraps sign_in() and persists the result, flipping the
#     `authenticated`/`mode` globals so the rest of the program can see
#     device state at a glance.
#   - refresh_authentication_token() exchanges a refresh token for a new
#     access token.
#   - get_authentication_token() is the single entry point everything else
#     calls: it reads the stored token, refreshes it if it's expired (or
#     about to expire), and falls back to a full re-login if the refresh
#     token itself is no longer valid. It only returns None if the device
#     is well and truly logged out.
#   - authenticated_request() wraps requests.* so any call that gets a 401
#     transparently forces a refresh (or re-login) and retries once.
# ---------------------------------------------------------------------------

def store_tokens(access_token, refresh_token, expiry):
    conn = sqlite3.connect('appdata.db')
    conn.execute(
        """
        INSERT OR REPLACE INTO server_auth
        (id, access_token, refresh_token, token_expiry)
        VALUES (1, ?, ?, ?)
        """,
        (access_token, refresh_token, expiry),
    )
    conn.commit()
    conn.close()


def clear_tokens():
    conn = sqlite3.connect('appdata.db')
    conn.execute("DELETE FROM server_auth WHERE id = 1")
    conn.commit()
    conn.close()


def sign_in(username: str, password: str, host: str):
    try:
        res = requests.post(f"{host}/login", json={"username": username, "password": password})
        if res.status_code == 200:
            return res.json()
        else:
            try:
                error_response = res.json()
                print("Sign-in failed: ", error_response)
            except json.JSONDecodeError:
                print("Sign-in failed with status code: ", res.status_code)
            return None

    except requests.RequestException as e:
        print("Error during sign-in: ", e)
        return None


def perform_login():
    """Full username/password login. Persists tokens on success and updates
    the `authenticated`/`mode` globals either way."""
    global authenticated, mode

    auth = sign_in(username, password, host)
    if not auth or "accessToken" not in auth or "refreshToken" not in auth or "accessTokenExpiration" not in auth:
        print("Authentication failed. Please check your credentials.")
        authenticated = False
        mode = "not_authenticated"
        clear_tokens()
        return False

    store_tokens(auth["accessToken"], auth["refreshToken"], auth["accessTokenExpiration"])
    authenticated = True
    mode = "ready"
    return True


def refresh_authentication_token(refresh_token: str):
    """Exchanges a refresh token for a new access token. Returns the parsed
    JSON on success, or None if the refresh token itself was rejected."""
    try:
        res = requests.post(
            f"{host}/refresh",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        if res.status_code == 200:
            refreshed = res.json()
            store_tokens(
                refreshed["accessToken"],
                refreshed["refreshToken"],
                refreshed["accessTokenExpiration"],
            )
            return refreshed

        print(f"Refresh failed with status {res.status_code} - refresh token is no longer valid")
        return None

    except requests.RequestException as e:
        print("Error during token refresh: ", e)
        return None


def get_authentication_token(force_refresh=False):
    """Returns a valid access token, refreshing or re-logging-in as needed.
    Returns None only if login itself fails (bad credentials / server down)."""
    global authenticated, mode

    conn = sqlite3.connect('appdata.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT access_token, refresh_token, token_expiry FROM server_auth ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None if not perform_login() else get_authentication_token()

    access_token, refresh_token, expiry_time = row

    try:
        expiry_time = float(expiry_time)
    except (TypeError, ValueError):
        expiry_time = 0  # unknown expiry -> treat as already expired

    needs_refresh = force_refresh or time() > (expiry_time - TOKEN_REFRESH_MARGIN)

    if not needs_refresh:
        authenticated = True
        return access_token

    # Token is expired/expiring or a caller explicitly asked for a fresh one.
    refreshed = refresh_authentication_token(refresh_token)
    if refreshed and "accessToken" in refreshed:
        authenticated = True
        return refreshed["accessToken"]

    # Refresh token no longer works -> the user has to log back in.
    print("Refresh token invalid or expired. Logging out.")
    authenticated = False
    mode = "not_authenticated"
    clear_tokens()

    if perform_login():
        return get_authentication_token()

    return None


def authenticated_request(method, path, **kwargs):
    """requests.* wrapper that attaches a valid bearer token and, on a 401,
    forces one token refresh/re-login cycle and retries once before giving up."""
    token = get_authentication_token()
    if token is None:
        raise AuthenticationError("Could not obtain an access token (login failed).")

    headers = kwargs.pop("headers", {}) or {}
    headers["Authorization"] = f"Bearer {token}"

    res = requests.request(method, f"{host}{path}", headers=headers, **kwargs)

    if res.status_code == 401:
        print("Got 401, forcing token refresh and retrying once")
        token = get_authentication_token(force_refresh=True)
        if token is None:
            raise AuthenticationError("Re-authentication failed after 401.")
        headers["Authorization"] = f"Bearer {token}"
        res = requests.request(method, f"{host}{path}", headers=headers, **kwargs)

    return res


def handleError(error):
    print("Error occurred: ", error)
    p.text("Error occurred: " + str(error) + "\n")
    return None


# ---------------------------------------------------------------------------
# Message printing / polling
# ---------------------------------------------------------------------------

async def print_messages():
    global mode
    mode = "printing"

    res = authenticated_request("GET", "/message", json={"status": "pending"})
    messages = res.json()

    for message in messages['data']:
        print(message["content"])
        p.text("\n")
        p.text("Name: " + message["name"] + "\n")
        p.text("Email: " + message["email"] + "\n")
        p.text("Timestamp: " + message["created_at"] + "\n")

        for elem in message["content"]:
            print(elem)
            if elem["type"] == "text":
                p.text(elem["content"] + "\n")
            elif elem["type"] == "image":
                p.image(load_print_image(elem["src"]))

        try:
            authenticated_request(
                "PATCH",
                "/confirm-receipt",
                json={"messages": [{"postId": message["post_id"], "email": message["email"]}]},
            )
        except AuthenticationError as e:
            print(f"Could not confirm receipt, not authenticated: {e}")
        except requests.RequestException as e:
            print(f"Error occurred while updating message status: {e}")

    mode = "ready"


async def detect_new_messages_available():
    try:
        res = authenticated_request("GET", "/message")
        messages = res.json()
        return len(messages['data']) > 0
    except AuthenticationError as e:
        print(f"Not authenticated, cannot check for messages: {e}")
        return False
    except requests.RequestException as e:
        print(f"Error occurred while checking for new messages: {e}")
        return False


def listen_for_new_messages():
    global mode

    while isActive:
        try:
            token = get_authentication_token()
        except AuthenticationError:
            token = None

        if token is None:
            # Couldn't get any token at all (login failing, e.g. bad creds
            # or server unreachable). Back off and try again rather than
            # spinning forever.
            mode = "not_authenticated"
    
            sleep(10)
            continue

        mode = "ready"
  

        try:
            client = sseclient.SSEClient(
                f"{host}/messages-available",
                headers={"Authorization": f"Bearer {token}"},
            )
        except Exception as e:
            print(f"Could not open event stream: {e}")
            sleep(5)
            continue

        try:
            for event in client:
                if event.event == "ping":
                    continue

                print(event.event, event.data)

                if event.event == "message-count":
                    try:
                        payload = json.loads(event.data)
                    except json.JSONDecodeError:
                        continue

                    if payload.get("hasMessages"):
                        mode = "waiting_for_print_confirmation"
                        if button.wait_for_press():
                            asyncio.run(print_messages())
                        break
                    else:
                        if button.is_pressed:
                            led.color = (1, 0, 0)
                            mode = "ready"

                # If the access token used for this SSE connection expires
                # while we're still listening, reconnect with a fresh one
                # rather than waiting for a 401 that SSE streams don't
                # reliably surface mid-stream.
                if time() > (get_token_expiry() - TOKEN_REFRESH_MARGIN):
                    print("Access token nearing expiry, reconnecting stream with a fresh token")
                    break
        except Exception as e:
            print(f"Event stream error: {e}")
            sleep(5)


def get_token_expiry():
    conn = sqlite3.connect('appdata.db')
    cursor = conn.cursor()
    cursor.execute("SELECT token_expiry FROM server_auth ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if not row or row[0] is None:
        return 0
    try:
        return float(row[0])
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
wait_for_system_ready()
intitialize_db()

mode = "ready"
perform_login()

listen_for_new_messages()