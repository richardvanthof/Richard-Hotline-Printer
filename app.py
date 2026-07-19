from gpiozero import RGBLED, Button
from escpos.printer import Usb
from PIL import Image
import json
from time import sleep
import sqlite3

messages = []
mode = "fetching"
authenticated = True
isActive = True
messages.append('{"id":1,"name":"John Doe","email":"john@doe.com","timestamp":"2023-10-01 12:00:00","message_body":[{"type":"image","src":"sample.jpg"},{"type":"text","content":"This is a sample message with an image and text."}]}')
messages.append('{"id":2,"name":"Jane Doe","email":"jane@doe.com","timestamp":"2023-10-01 12:40:00","message_body":[{"type":"image","src":"sample.jpg"},{"type":"text","content":"This is a sample message with an image and text."}]}')

p = Usb(0x0416, 0x5011, 0)
led = RGBLED(red=9, green=10, blue=11)
button = Button(2)


def load_print_image(image_path, max_width=400):
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        if image.width > max_width:
            new_height = round(image.height * max_width / image.width)
            image = image.resize((max_width, new_height), Image.LANCZOS)
        return image

while(isActive):
    led.green = .1
    if mode == "fetching":
        led.blue = 0/100

        if(len(messages) > 0):
            # slowly increase intensity of blue
            led.green = 1
            button.wait_for_press()
            mode = "printing"
    elif mode == "printing":
        for message in messages:
            message = json.loads(message)
            p.text("\n")
            p.text("Name: " + message["name"] + "\n")
            p.text("Email: " + message["email"] + "\n")
            p.text("Timestamp: " + message["timestamp"] + "\n")
            for body in message["message_body"]:
                if body["type"] == "text":
                    p.text("Message: " + body["content"] + "\n")
                elif body["type"] == "image":
                    p.image(load_print_image(body["src"]))
            
        messages = []
        mode = "fetching"


# # Create a cursor object to execute SQL queries
# cursor = conn.cursor()

# # Execute a simple SQL command to create a table
# cursor.execute(
#     """CREATE TABLE IF NOT EXISTS users
#                 (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)"""
# )

# # Commit the changes and close the connection
# conn.commit()
# conn.close()

# led = RGBLED(red=9, green=10, blue=11)
# button = Button(2)

# print("Press button to start")
# button.wait_for_press()
# print("Button was pressed")

# led.red = 1  # full red
# sleep(1)
# led.red = 0.5  # half red
# sleep(1)

# print('green')
# led.color = (0, 1, 0)  # full green
# sleep(1)
# print('magenta')
# led.color = (1, 0, 1)  # magenta
# sleep(1)
# print('yellow')
# led.color = (1, 1, 0)  # yellow
# sleep(1)
# print('cyan')
# led.color = (0, 1, 1)  # cyan
# sleep(1)
# print('white')
# led.color = (1, 1, 1)  # white
# sleep(1)

# led.color = (0, 0, 0)  # off
# sleep(1)

# # slowly increase intensity of blue
# for n in range(100):
#     led.blue = n/100
#     sleep(0.1)
