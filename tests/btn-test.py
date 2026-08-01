from gpiozero import Button
from time import sleep

button = Button(2)

print("Press button to start")
button.wait_for_press()
print("Button was pressed")
sleep(3)