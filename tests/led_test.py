from gpiozero import RGBLED, Button
from time import sleep

led = RGBLED(red=9, green=10, blue=11)
button = Button(2)

# print("Press button to start")
# button.wait_for_press()
# print("Button was pressed")

led.red = 1  # full red
sleep(1)
led.red = 0.5  # half red
sleep(1)

print('green')
led.color = (0, 1, 0)  # full green
sleep(1)
print('magenta')
led.color = (1, 0, 1)  # magenta
sleep(1)
print('yellow')
led.color = (1, 1, 0)  # yellow
sleep(1)
print('cyan')
led.color = (0, 1, 1)  # cyan
sleep(1)
print('white')
led.color = (1, 1, 1)  # white
sleep(1)

led.color = (0, 0, 0)  # off
sleep(1)

# slowly increase intensity of blue
for n in range(100):
    led.blue = n/100
    sleep(0.1)
