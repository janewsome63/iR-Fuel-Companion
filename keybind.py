import time
import keyboard


class Vars:
    button = "None"
    error_count = 0


def keys():
    while True:
        try:
            key = keyboard.get_hotkey_name()
        except AttributeError:
            key = ""
            time.sleep(1)
        if not key.endswith('ctrl') and not key.endswith('shift') and not key.endswith('alt') and not key.endswith('alt gr'):
            if key:
                Vars.button = key
            if not key:
                Vars.button = "None"
        time.sleep(1 / 20)
