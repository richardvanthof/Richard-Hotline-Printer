from gpiozero import LED, Button
from time import sleep

led = LED(23)

led.on()

sleep(5)  # wait for 5 seconds
# # slowly increase intensity of blue
# for n in range(100):
#     led = n/100
#     sleep(0.1)
