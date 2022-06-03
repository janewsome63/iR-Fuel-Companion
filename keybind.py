#import pygame
import time
import keyboard
#from pynput.keyboard import Key, Listener

class vars():
	button = "None"
	error_count = 0


#def on_press(key):
#    vars.button = '{0}'.format(key)

#def on_release(key):
#    vars.button = "None"

#def gamepad():
#    pygame.init()
#    clock = pygame.time.Clock()
#    pygame.joystick.init()
#    button = True
#
#    while True:
#        for event in pygame.event.get(): # User did something.
#            if event.type == pygame.JOYBUTTONDOWN:
#                vars.button = event.__dict__
#            elif event.type == pygame.JOYHATMOTION:
#                if event.__dict__['value'] == (0, 0):
#                    vars.button = "None"
#                else:
#                    vars.button = event.__dict__
#            else:
#                vars.button = "None"

        # Get count of joysticks.
#        joystick_count = pygame.joystick.get_count()
#        for i in range(joystick_count):
#            joystick = pygame.joystick.Joystick(i)
#            joystick.init()

        # Limit to 20 frames per second.
#        clock.tick(20)

def keys():
    # Collect events until released
#    with Listener(on_press=on_press, on_release=on_release) as listener:
#        listener.join()
	while True:
		try:
			key = keyboard.get_hotkey_name()
		except:
			time.sleep(1)
		if not key.endswith('ctrl') and not key.endswith('shift') and not key.endswith('alt') and not key.endswith('alt gr'):
			if key:
				vars.button = key
			if not key:
				vars.button = "None"
		time.sleep(1/20)