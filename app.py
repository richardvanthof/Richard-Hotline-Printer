from gpiozero import RGBLED, Button
from escpos.printer import Usb
from PIL import Image
import requests
import os
import json
import asyncio
from time import sleep, time
import sqlite3
import sseclient
from io import BytesIO

messages = []
mode = None
authenticated = True
isActive = True
# messages.append()
# messages.append('{"id":2,"name":"Jane Doe","email":"jane@doe.com","timestamp":"2023-10-01 12:40:00","message_body":[{"type":"image","src":"sample.jpg"},{"type":"text","content":"This is a sample message with an image and text."}]}')


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
led = RGBLED(red=9, green=10, blue=11)
button = Button(2)

# server credentials
host = os.environ.get("HOST")
username = os.environ.get("USERNAME")
password = os.environ.get("PASSWORD")

# init
# check if the printer is connected, if internet connection is available, has paper and is authenticated to the server
# printer ready: wait for messages
# if messages area available, activate notifcation led and wait for button press
#if button pressed, fetch all messsages, print messages and mark the messages as printed on the server, then go back to waiting for messages
def printer_connected():
    # check if the printer is connected
    try:
        p._raw(b'\x1D\x61\x01')  # test command to check if printer is connected
        return True
    except Exception as e:
        print("Printer not connected: ", e)
        sleep(5)
        printer_connected()

def check_internet_connection():
    import socket
    try:
        # connect to the host -- tells us if the host is actually reachable
        socket.create_connection(("www.google.com", 80))
        return True
    except OSError:
        pass
    check_internet_connection()

def check_paper_status():
    # check if the printer has paper
    try:
        p._raw(b'\x1D\x61\x01')  # test command to check if printer is connected
        return True
    except Exception as e:
        print("Printer not connected: ", e)
        check_paper_status()

def intitialize_db():
    
    conn = sqlite3.connect('appdata.db')
    
    cursor = conn.cursor()
    # cursor.execute(
    #     """CREATE TABLE IF NOT EXISTS messages
    #                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT, timestamp TEXT, message_body TEXT)"""
    # )
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

def refresh_authentication_token(refreshToken:str):
    try:
        res = requests.post(
            f"{host}/refresh",
            json={"refresh_token": refreshToken},
            headers={"Authorization": f"Bearer {refreshToken}"}
        )
        if res.status_code == 200:
            connj = sqlite3.connect('appdata.db')
            cursorj = connj.cursor()
            refreshed_tokens = res.json()
            cursorj.execute(
                """UPDATE server_auth SET refresh_token = ?, token_expiry = ? WHERE id = 1""",
                (refreshed_tokens.get("accessToken"), refreshed_tokens.get("accessTokenExpiration"))
            )
            connj.commit()
            connj.close();

            return res.json()
    except Exception as e:
        print("Error during token refresh: ", e)


def get_authentication_token():
    conn = sqlite3.connect('appdata.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT access_token, refresh_token, token_expiry FROM server_auth ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        access_token, refresh_token, expiry_time = row
        if expiry_time is not None:
            try:
                expiry_time = float(expiry_time)
            except (TypeError, ValueError):
                expiry_time = None

        if expiry_time is not None and time() > expiry_time:
            return refresh_authentication_token(refresh_token)
        else:
            return access_token
    else:
        return None

def sign_in(username:str, password:str, host:str):
    try:
        res = requests.post(f"{host}/login", json={"username": username, "password": password})
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print("Error during sign-in: ", e)
    

# check if the printer is connected, if internet connection is available, has paper and is authenticated to the server
mode = "initializing"



## INITIALIZE PRINTER
mode = "initializing"
printer_connected()
check_internet_connection()
check_paper_status()
intitialize_db()
mode = "ready"
try:
    res = sign_in(username, password, host)
except Exception as e:
    print("Error during sign-in: ", e)
    res = None

access_token = res["accessToken"] if res else None
refresh_token = res["refreshToken"] if res else None
token_expiry = res.get("accessTokenExpiration", None) if res else None
# store the tokens in the database
conn = sqlite3.connect('appdata.db')
cursor = conn.cursor()
cursor.execute(
    """INSERT OR REPLACE INTO server_auth (id, access_token, refresh_token, token_expiry) VALUES (1, ?, ?, ?)""",
    (access_token, refresh_token, token_expiry)
)
conn.commit()
conn.close()


conn = sqlite3.connect("appdata.db")
cursor = conn.cursor()

cursor.execute(
    "SELECT access_token, refresh_token, token_expiry FROM server_auth ORDER BY id DESC LIMIT 1"
)
row = cursor.fetchone()




async def print_messages():
    res = requests.get(
            f"{host}/message", 
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "status": "pending"
            }
        )
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
                token = get_authentication_token();
                res = requests.patch(
                    f"{host}/confirm-receipt", 
                    headers={"Authorization": f"Bearer {token}"}, 
                    json={"messages": [
                            {
                                "postId": message["post_id"],
                                "email": message["email"],
                            }
                        ]
                        }
                    )
            except requests.RequestException as e:
                print(f"Error occurred while updating message status: {e}")
        messages = []
        # mode = "fetching"

async def detect_new_messages_available():
    try:
        token = get_authentication_token()
        res = requests.get(f"{host}/message", headers={"Authorization": f"Bearer {token}"})
        messages = res.json()
        return len(messages['data']) > 0
    except requests.RequestException as e:
        print(f"Error occurred while checking for new messages: {e}")
        return False


def listen_for_new_messages():
    isIdle = True
    while isActive:
        led.color = (0, 0, 0)  # Blue for new messages
        client = sseclient.SSEClient(
            f"{host}/messages-available",
            headers={"Authorization": f"Bearer {get_authentication_token()}"},
        )

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
                    led.color = (1, 0, 1)  # Blue for new messages
                    if button.wait_for_press():
                        asyncio.run(print_messages())
                    break
                else:
                    if button.is_pressed:
                        led.color = (1, 0, 0)
                        
                    

listen_for_new_messages()