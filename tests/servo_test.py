# pin pwm: 13
from gpiozero import Servo
from time import sleep

servo = Servo(13)

servo.min()
print('servo min')
sleep(1)
servo.mid()
print('servo mid')
sleep(1)
servo.max()
print('servo max')
sleep(1)
servo.min()
