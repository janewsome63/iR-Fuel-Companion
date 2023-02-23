import configparser
import logging
import math
import os
import threading
import time
import urllib.request
from datetime import datetime
import irsdk
import keyboard
import pythoncom
import win32com.client as wincl
import gui
import keybind

# Variable storages
# General
state = {
    "connected": False,
    "imperial": False,
    "reset_laps": False,
    "separator": True,
    "spectator": False,
    "spotter": False,
    "lap_trigger": False,
    "version": "v0.2.7",
}

# Language related
lang = {
    "no_connection": "no eye racing connection",
    "separator_a": "=" * 138,
    "separator_b": "-" * 138,
}

# Fuel related
fuel = {
    "eco": 0.0,
    "eco_req": 0.0,
    "laps_left": 0.0,
    "laps_left_avg": 0.0,
    "laps_left_max": 0.0,
    "laps_left_fixed": 0.0,
    "last_level": 0.0,
    "last_level_pit": 0.0,
    "level_current": 0.0,
    "level_full": 0.0,
    "level_req": 0.0,
    "level_req_avg": 0.0,
    "level_req_max": 0.0,
    "level_req_fixed": 0.0,
    "pct_current": 0.0,
    "pct_max": 0.0,
    "stint_eco": 0.0,
    "stint_used": 0.0,
    "stint_used_avg": 0.0,
    "stops": 0,
    "stops_avg": 0,
    "stops_max": 0,
    "stops_fixed": 0,
    "used_lap": 0.0,
    "used_lap_avg": 0.0,
    "used_lap_max": 0.0,
    "used_lap_fixed": 0.0,
    "used_lap_list": [],
    "used_lap_req": 0.0,
    "window_lap": 0,
    "window_lap_avg": 0,
    "window_lap_max": 0,
    "window_lap_fixed": 0,
}

telem = {
    "driver_idx": 0,
    "flag_hex": 0x00000000,
    "flag_list": [],
    "engine_hex": 0x00000000,
    "engine_list": [],
    "track_length": 0,
    "lap_next": 0,
    "lap_time_prev": 0.0,
    "lap_times_stint": [],
    "lap_times_stint_avg": 0.0,
    "lap_times_total": [],
    "lap_times_total_avg": 0.0,
    "laps_completed": 0,
    "laps_remaining": 0,
    "last_track_temp": 0.0,
    "last_air_temp": 0.0,
    "oil_temp_warning": 999.0,
    "oil_trigger": False,
    "oil_warned": False,
    "oil_warning_prev": False,
    "session": "",
    "session_time_prev": 0.0,
    "stint_laps": 0,
    "surface": 0,
    "timer_start": 0.0,
    "water_temp_warning": 999.0,
    "water_trigger": False,
    "water_warned": False,
    "water_warning_prev": False,
}


# Unit Conversion Ref:
#   l * 0.264172 = gal
#   km * 0.621371 = mi
#   m * 0.000621371 = mi
#   (c * 1.8) + 32 = f
#   kph * 0.6213711922 = mph
#   rad * 57.295779513 = deg
#   m/s * 2.2369362920544025 = mph
#   Hg * 3.38639 = kPa
#   kg/m^3 * 0.062427960576145 = lb/ft^3
#   km/l * 2.352145833 = mpg

# Unit related functions
# Return converted temperature
def temperature(value, style):
    if state['imperial']:
        if style == "string":
            return str(round((value * 1.8) + 32, 2)) + "f"
        if style == "number":
            return round((value * 1.8) + 32, 2)
    else:
        if style == "string":
            return str(round(value, 2)) + "c"
        elif style == "number":
            return round(value, 2)


# Return converted speed
def speed(value):
    if state['imperial']:
        return str(round(value * 2.2369362920544025, 1)) + "mph"
    else:
        return str(round(value * 3.6, 1)) + "kph"


# Return converted pressure
def pressure(value):
    if state['imperial']:
        return str(round(value, 1)) + "hg"
    else:
        return str(round(value * 3.38639, 1)) + "kpa"


# Return converted density
def density(value):
    if state['imperial']:
        return str(round(value * 0.062427960576145, 2)) + "lb/ft^3"
    else:
        return str(round(value, 2)) + "kg/m^3"


# Return converted distance
def distance(value, magnitude):
    if state['imperial']:
        if magnitude == "m":
            return str(round(value * 0.000621371, 2)) + "mi"
        elif magnitude == "km":
            return str(round(value * 0.621371, 2)) + "mi"
    else:
        if magnitude == "m":
            return str(round(value * 0.001, 2)) + "km"
        elif magnitude == "km":
            return str(round(value, 2)) + "km"


# Return converted volume
def volume(value, suffix):
    if state['imperial']:
        if suffix == "short":
            return str(round(value * 0.264172, 3)) + "gal"
        elif suffix == "long":
            return str(round(value * 0.264172, 3)) + " gallons"
    else:
        if suffix == "short":
            return str(round(value, 3)) + "l"
        elif suffix == "long":
            return str(round(value, 3)) + " liters"


# Return converted economy
def economy(value):
    if state['imperial']:
        return str(round(value * 2.352145833, 2)) + "mpg"
    else:
        return str(round(value, 2)) + "km/l"


# Return formatted percentage
def percent(value):
    return str(round(value * 100, 2)) + "%"


# Return formatted time
def duration(value):
    return str(round(value, 3)) + "s"


# Return a cardinal wind direction
def wind():
    wind_deg = ir['WindDir'] * 57.295779513
    if wind_deg >= 337.5 or wind_deg <= 22.5:
        return "N"
    elif 22.5 < wind_deg < 67.5:
        return "NE"
    elif 67.5 <= wind_deg <= 112.5:
        return "E"
    elif 112.5 < wind_deg < 157.5:
        return "SE"
    elif 157.5 <= wind_deg <= 202.5:
        return "S"
    elif 202.5 < wind_deg < 247.5:
        return "SW"
    elif 247.5 <= wind_deg <= 292.5:
        return "W"
    elif 292.5 < wind_deg < 337.5:
        return "NW"
    else:
        return "N/A"


# Control listening thread
def controls_thread():
    while True:
        # Pause after binding to prevent immediate trigger
        while gui.Binds.pause_count > 0:
            gui.Binds.pause_count = gui.Binds.pause_count - 1
            time.sleep(0.5)

        # Toggle auto fuel
        if gui.Binds.keys["auto_fuel"] == keybind.Vars.button:
            time.sleep(0.25)
            if gui.Vars.checkboxes["auto_fuel"]:
                gui.event('check-auto_fuel', 0)
                threading.Thread(target=speech_thread, args=("auto fuel disabled",)).start()
            elif not gui.Vars.checkboxes["auto_fuel"]:
                gui.event('check-auto_fuel', 1)
                threading.Thread(target=speech_thread, args=("auto fuel enabled",)).start()
            time.sleep(0.75)

        # Cycle auto fuel type
        if gui.Binds.keys["auto_fuel_cycle"] == keybind.Vars.button:
            time.sleep(0.25)
            if gui.Vars.combo["auto_fuel_type"] == "Fixed":
                gui.event('combo-auto_fuel_type', "Average")
                threading.Thread(target=speech_thread, args=("using average usage for auto fuel",)).start()
            elif gui.Vars.combo["auto_fuel_type"] == "Average":
                gui.event('combo-auto_fuel_type', "Max")
                threading.Thread(target=speech_thread, args=("using max usage for auto fuel",)).start()
            elif gui.Vars.combo["auto_fuel_type"] == "Max":
                gui.event('combo-auto_fuel_type', "Fixed")
                threading.Thread(target=speech_thread, args=("using fixed usage for auto fuel",)).start()
            time.sleep(0.75)

        # Set auto fuel to average
        if gui.Binds.keys["auto_fuel_average"] == keybind.Vars.button:
            time.sleep(0.25)
            gui.event('combo-auto_fuel_type', "Average")
            threading.Thread(target=speech_thread, args=("using average usage for auto fuel",)).start()
            time.sleep(0.75)

        # Set auto fuel to max
        if gui.Binds.keys["auto_fuel_max"] == keybind.Vars.button:
            time.sleep(0.25)
            gui.event('combo-auto_fuel_type', "Max")
            threading.Thread(target=speech_thread, args=("using max usage for auto fuel",)).start()
            time.sleep(0.75)

        # Set auto fuel to fixed
        if gui.Binds.keys["auto_fuel_fixed"] == keybind.Vars.button:
            time.sleep(0.25)
            gui.event('combo-auto_fuel_type', "Fixed")
            threading.Thread(target=speech_thread, args=("using fixed usage for auto fuel",)).start()
            time.sleep(0.75)

        # Set required fuel
        if gui.Binds.keys["set_required"] == keybind.Vars.button:
            time.sleep(0.25)
            if state['connected']:
                if gui.Vars.combo["auto_fuel_type"] == "Average":
                    if (telem['laps_remaining'] + gui.Vars.spin["extra_laps"]) * fuel['used_lap_avg'] < ir['FuelLevel']:
                        fuel_add = 0.0
                    else:
                        fuel_add = fuel['level_req_avg'] + (fuel['used_lap_avg'] * gui.Vars.spin["extra_laps"])
                elif gui.Vars.combo["auto_fuel_type"] == "Max":
                    if (telem['laps_remaining'] + gui.Vars.spin["extra_laps"]) * fuel['used_lap_max'] < ir['FuelLevel']:
                        fuel_add = 0.0
                    else:
                        fuel_add = fuel['level_req_max'] + (fuel['used_lap_max'] * gui.Vars.spin["extra_laps"])
                else:
                    if (telem['laps_remaining'] + gui.Vars.spin["extra_laps"]) * fuel['used_lap_fixed'] < ir['FuelLevel']:
                        fuel_add = 0.0
                    else:
                        fuel_add = fuel['level_req_fixed'] + (fuel['used_lap_fixed'] * gui.Vars.spin["extra_laps"])
                if fuel_add + fuel['last_level'] <= ir['FuelLevel']:
                    ir.pit_command(11)
                if fuel_add + fuel['last_level'] > ir['FuelLevel']:
                    ir.pit_command(2, int(round(fuel_add, 0)))
                speech = threading.Thread(target=speech_thread, args=("fuel set",))
                speech.start()
            else:
                speech = threading.Thread(target=speech_thread, args=(lang['no_connection'],))
                speech.start()
            time.sleep(0.75)

        # Toggle tts fuel updates
        if gui.Binds.keys["tts_fuel"] == keybind.Vars.button:
            time.sleep(0.25)
            if gui.Vars.checkboxes["tts_fuel"]:
                gui.event('check-tts_fuel', 0)
                threading.Thread(target=speech_thread, args=("speech fuel updates disabled",)).start()
            elif not gui.Vars.checkboxes["tts_fuel"]:
                gui.event('check-tts_fuel', 1)
                threading.Thread(target=speech_thread, args=("speech fuel updates enabled",)).start()
            time.sleep(0.75)

        # Toggle print fuel updates
        if gui.Binds.keys["txt_fuel"] == keybind.Vars.button:
            time.sleep(0.25)
            if gui.Vars.checkboxes["txt_fuel"]:
                gui.event('check-txt_fuel', 0)
                threading.Thread(target=speech_thread, args=("text fuel updates disabled",)).start()
            elif not gui.Vars.checkboxes["txt_fuel"]:
                gui.event('check-txt_fuel', 1)
                threading.Thread(target=speech_thread, args=("text fuel updates enabled",)).start()
            time.sleep(0.75)

        # Toggle temperature updates
        if gui.Binds.keys["temp_updates"] == keybind.Vars.button:
            time.sleep(0.25)
            if gui.Vars.checkboxes["temp_updates"]:
                gui.event('check-temp_updates', 0)
                threading.Thread(target=speech_thread, args=("temperature updates disabled",)).start()
            elif not gui.Vars.checkboxes["temp_updates"]:
                gui.event('check-temp_updates', 1)
                threading.Thread(target=speech_thread, args=("temperature updates enabled",)).start()
            time.sleep(0.75)

        # Report current temperatures
        if gui.Binds.keys["temp_report"] == keybind.Vars.button:
            time.sleep(0.25)
            if state['connected']:
                threading.Thread(target=speech_thread, args=("air temp is " + str(round(temperature(ir['AirTemp'], "number"))) + " and track temp is " + str(round(temperature(ir['TrackTempCrew'], "number"))),)).start()
            else:
                threading.Thread(target=speech_thread, args=(lang['no_connection'],)).start()
            time.sleep(0.75)

        # Print previous lap usage info
        if gui.Binds.keys["previous_usage"] == keybind.Vars.button:
            time.sleep(0.25)
            if state['connected']:
                ir.chat_command(1)
                time.sleep(0.05)
                keyboard.write("## Previous lap - " + str(round(fuel['laps_left'], 2)) + " laps, " + volume(fuel['used_lap'], "short") + ", " + economy(fuel['eco']) + ", " +
                               volume(fuel['level_req'], "short") + "(" + str(fuel['stops']) + ", " + str(fuel['window_lap']) + ") extra ##")
                time.sleep(0.05)
                keyboard.send('enter')
                time.sleep(0.05)
                ir.chat_command(3)
            else:
                threading.Thread(target=speech_thread, args=(lang['no_connection'],)).start()
            time.sleep(0.75)

        # Print required usage info
        if gui.Binds.keys["required_usage"] == keybind.Vars.button:
            time.sleep(0.25)
            if state['connected']:
                ir.chat_command(1)
                time.sleep(0.05)
                if gui.Vars.input["fixed_usage"] > 0.0:
                    keyboard.write("## Required - " + str(telem['laps_remaining']) + " laps, " + volume(fuel['used_lap_req'], "short") + ", " + economy(fuel['eco_req']) + ", " +
                                   volume(fuel['level_req_avg'], "short") + "(" + str(fuel['stops_avg']) + ", " + str(fuel['window_lap_avg']) + ") avg, " +
                                   volume(fuel['level_req_max'], "short") + "(" + str(fuel['stops_max']) + ", " + str(fuel['window_lap_max']) + ") max, " +
                                   volume(fuel['level_req_fixed'], "short") + "(" + str(fuel['stops_fixed']) + ", " + str(fuel['window_lap_fixed']) + ") fixed ##")
                else:
                    keyboard.write("## Required - " + str(telem['laps_remaining']) + " laps, " + volume(fuel['used_lap_req'], "short") + ", " + economy(fuel['eco_req']) + ", " +
                                   volume(fuel['level_req_avg'], "short") + "(" + str(fuel['stops_avg']) + ", " + str(fuel['window_lap_avg']) + ") avg, " +
                                   volume(fuel['level_req_max'], "short") + "(" + str(fuel['stops_max']) + ", " + str(fuel['window_lap_max']) + ") max ##")
                time.sleep(0.05)
                keyboard.send('enter')
                time.sleep(0.05)
                ir.chat_command(3)
            else:
                threading.Thread(target=speech_thread, args=(lang['no_connection'],)).start()
            time.sleep(0.75)
        time.sleep(1 / 20)


# Save binding
def bind_set(bind, event):
    if keybind.Vars.button == "esc":
        gui.event(event, "")
    elif keybind.Vars.button != "None":
        getattr(gui.Binds, "keys")[bind] = keybind.Vars.button
        controls_name(bind)
        gui.event(event, "")


# Save binding name
def controls_name(bind):
    button = getattr(gui.Binds, "keys")[bind]
    if not isinstance(button, dict):
        if button == "":
            getattr(gui.Binds, "names")[bind] = "Bind"
        else:
            getattr(gui.Binds, "names")[bind] = button
        # elif 'value' in button:
        #     getattr(gui.Binds, "names")[bind] = "Joy " + str(button['instance_id']) + " Hat " + str(button['value']))
        # else:
        #     getattr(gui.Binds, "names")[bind] = "Joy " + str(button['instance_id']) + " Button " + str(button['button']))


# Binding listening thread
def binding_thread():
    while True:
        if not gui.Binds.binding:
            time.sleep(1 / 2)
        else:
            while gui.Binds.binding:
                if gui.Binds.recording["auto_fuel"]:
                    bind_set('auto_fuel', 'bind-auto_fuel')
                elif gui.Binds.recording["auto_fuel_cycle"]:
                    bind_set('auto_fuel_cycle', 'bind-auto_fuel_cycle')
                elif gui.Binds.recording["auto_fuel_average"]:
                    bind_set('auto_fuel_average', 'bind-auto_fuel_average')
                elif gui.Binds.recording["auto_fuel_max"]:
                    bind_set('auto_fuel_max', 'bind-auto_fuel_max')
                elif gui.Binds.recording["auto_fuel_fixed"]:
                    bind_set('auto_fuel_fixed', 'bind-auto_fuel_fixed')
                elif gui.Binds.recording["set_required"]:
                    bind_set('set_required', 'bind-set_required')
                elif gui.Binds.recording["tts_fuel"]:
                    bind_set('tts_fuel', 'bind-tts_fuel')
                elif gui.Binds.recording["txt_fuel"]:
                    bind_set('txt_fuel', 'bind-txt_fuel')
                elif gui.Binds.recording["temp_updates"]:
                    bind_set('temp_updates', 'bind-temp_updates')
                elif gui.Binds.recording["temp_report"]:
                    bind_set('temp_report', 'bind-temp_report')
                elif gui.Binds.recording["previous_usage"]:
                    bind_set('previous_usage', 'bind-previous_usage')
                elif gui.Binds.recording["required_usage"]:
                    bind_set('required_usage', 'bind-required_usage')
                time.sleep(1 / 20)


# Read settings.ini
def read_config():
    config = configparser.ConfigParser()
    config.read(gui.Vars.user_dir + '\\settings.ini')

    # Fueling
    if config.has_option('Fueling', 'auto_fuel'):
        gui.Vars.checkboxes["auto_fuel"] = config.getboolean('Fueling', 'auto_fuel')
    if config.has_option('Fueling', 'auto_fuel_type'):
        gui.Vars.combo["auto_fuel_type"] = config.get('Fueling', 'auto_fuel_type')
    if config.has_option('Fueling', 'fixed_usage'):
        gui.Vars.input["fixed_usage"] = config.getfloat('Fueling', 'fixed_usage')
    if config.has_option('Fueling', 'extra_laps'):
        gui.Vars.spin["extra_laps"] = config.getint('Fueling', 'extra_laps')

    # Updates
    if config.has_option('Updates', 'check_updates'):
        gui.Vars.checkboxes["check_updates"] = config.getboolean('Updates', 'check_updates')
    if config.has_option('Updates', 'engine_warnings'):
        gui.Vars.checkboxes["engine_warnings"] = config.getboolean('Updates', 'engine_warnings')
    if config.has_option('Updates', 'oil_threshold'):
        gui.Vars.input["oil_threshold"] = config.getfloat('Updates', 'oil_threshold')
    if config.has_option('Updates', 'water_threshold'):
        gui.Vars.input["water_threshold"] = config.getfloat('Updates', 'water_threshold')
    if config.has_option('Updates', 'tts_fuel'):
        gui.Vars.checkboxes["tts_fuel"] = config.getboolean('Updates', 'tts_fuel')
    if config.has_option('Updates', 'txt_fuel'):
        gui.Vars.checkboxes["txt_fuel"] = config.getboolean('Updates', 'txt_fuel')
    if config.has_option('Updates', 'temp_updates'):
        gui.Vars.checkboxes["temp_updates"] = config.getboolean('Updates', 'temp_updates')

    # Practice
    if config.has_option('Practice', 'laps'):
        gui.Vars.spin["practice_laps"] = config.getint('Practice', 'laps')
    if config.has_option('Practice', 'fuel_percent'):
        gui.Vars.spin["practice_fuel_percent"] = config.getint('Practice', 'fuel_percent')

    # Controls
    if config.has_option('Controls', 'auto_fuel_toggle'):
        gui.Binds.keys["auto_fuel"] = config.get('Controls', 'auto_fuel_toggle')
        controls_name('auto_fuel')
    if config.has_option('Controls', 'auto_fuel_cycle'):
        gui.Binds.keys["auto_fuel_cycle"] = config.get('Controls', 'auto_fuel_cycle')
        controls_name('auto_fuel_cycle')
    if config.has_option('Controls', 'auto_fuel_average'):
        gui.Binds.keys["auto_fuel_average"] = config.get('Controls', 'auto_fuel_average')
        controls_name('auto_fuel_average')
    if config.has_option('Controls', 'auto_fuel_max'):
        gui.Binds.keys["auto_fuel_max"] = config.get('Controls', 'auto_fuel_max')
        controls_name('auto_fuel_max')
    if config.has_option('Controls', 'auto_fuel_fixed'):
        gui.Binds.keys["auto_fuel_fixed"] = config.get('Controls', 'auto_fuel_fixed')
        controls_name('auto_fuel_fixed')
    if config.has_option('Controls', 'set_required'):
        gui.Binds.keys["set_required"] = config.get('Controls', 'set_required')
        controls_name('set_required')
    if config.has_option('Controls', 'tts_fuel'):
        gui.Binds.keys["tts_fuel"] = config.get('Controls', 'tts_fuel')
        controls_name('tts_fuel')
    if config.has_option('Controls', 'txt_fuel'):
        gui.Binds.keys["txt_fuel"] = config.get('Controls', 'txt_fuel')
        controls_name('txt_fuel')
    if config.has_option('Controls', 'temp_updates'):
        gui.Binds.keys["temp_updates"] = config.get('Controls', 'temp_updates')
        controls_name('temp_updates')
    if config.has_option('Controls', 'temp_report'):
        gui.Binds.keys["temp_report"] = config.get('Controls', 'temp_report')
        controls_name('temp_report')
    if config.has_option('Controls', 'previous_usage'):
        gui.Binds.keys["previous_usage"] = config.get('Controls', 'previous_usage')
        controls_name('previous_usage')
    if config.has_option('Controls', 'required_usage'):
        gui.Binds.keys["required_usage"] = config.get('Controls', 'required_usage')
        controls_name('required_usage')


# TTS thread
def speech_thread(text):
    pythoncom.CoInitialize()
    speech = wincl.Dispatch("SAPI.SpVoice")
    speech.Speak(text)


# Flag and engine warning thread
def warnings_thread():
    flag_hexes = {
        "checkered": 0x00000001,
        "white": 0x00000002,
        "green": 0x00000004,
        "yellow": 0x00000008,
        "red": 0x00000010,
        "blue": 0x00000020,
        "debris": 0x00000040,
        "crossed": 0x00000080,
        "yellow_waving": 0x00000100,
        "one_lap_to_green": 0x00000200,
        "green_held": 0x00000400,
        "ten_to_go": 0x00000800,
        "five_to_go": 0x00001000,
        "random_waving": 0x00002000,
        "caution": 0x00004000,
        "caution_waving": 0x00008000,
        "black": 0x00010000,
        "disqualify": 0x00020000,
        "serviceable": 0x00040000,
        "furled": 0x00080000,
        "repair": 0x00100000,
        "start_hidden": 0x10000000,
        "start_ready": 0x20000000,
        "start_set": 0x40000000,
        "start_go": 0x80000000,
    }
    engine_hexes = {
        "water_temp_warning": 0x01,
        "fuel_pressure_warning": 0x02,
        "oil_pressure_warning": 0x04,
        "engine_stalled": 0x08,
        "pit_speed_limiter": 0x10,
        "rev_limiter_active": 0x20,
        "oil_temp_warning": 0x40,
    }

    # Add current flag to list
    def flag_compare(name):
        if telem['flag_hex'] & flag_hexes[name] == flag_hexes[name]:
            telem['flag_list'].append(name)

    # Add current engine warning to list
    def engine_compare(name):
        if telem['engine_hex'] & engine_hexes[name] == engine_hexes[name]:
            telem['engine_list'].append(name)

    # Run comparisons
    while state['connected']:
        telem['flag_list'] = []
        flag_compare("checkered")
        flag_compare("white")
        flag_compare("green")
        flag_compare("yellow")
        flag_compare("red")
        flag_compare("blue")
        flag_compare("debris")
        flag_compare("crossed")
        flag_compare("yellow_waving")
        flag_compare("one_lap_to_green")
        flag_compare("green_held")
        flag_compare("ten_to_go")
        flag_compare("five_to_go")
        flag_compare("random_waving")
        flag_compare("caution")
        flag_compare("caution_waving")
        flag_compare("black")
        flag_compare("disqualify")
        flag_compare("serviceable")
        flag_compare("furled")
        flag_compare("repair")
        flag_compare("start_hidden")
        flag_compare("start_ready")
        flag_compare("start_set")
        flag_compare("start_go")

        telem['engine_list'] = []
        engine_compare("water_temp_warning")
        engine_compare("fuel_pressure_warning")
        engine_compare("oil_pressure_warning")
        engine_compare("engine_stalled")
        engine_compare("pit_speed_limiter")
        engine_compare("rev_limiter_active")
        engine_compare("oil_temp_warning")
        time.sleep(1)


# Fuel calculations
def fuel_calc():
    # Current fuel usage
    if fuel['level_current'] < fuel['last_level']:
        fuel['used_lap'] = fuel['last_level'] - fuel['level_current']
    elif fuel['level_current'] > fuel['last_level']:
        fuel['used_lap'] = fuel['last_level_pit'] - fuel['level_current']

    # Required fuel usage
    if telem['laps_remaining'] > 0:
        fuel['used_lap_req'] = fuel['level_current'] / telem['laps_remaining']
    else:
        fuel['used_lap_req'] = 0.0

    # Current fuel economy
    fuel['eco'] = telem['track_length'] / fuel['used_lap']

    # Required fuel economy
    fuel['eco_req'] = (telem['track_length'] * telem['laps_remaining']) / fuel['level_current']

    # Only do these actions while not in the pits, under caution, or on out lap
    if ir['CarIdxPaceLine'][telem['driver_idx']] == -1 and ir['CarIdxTrackSurface'][telem['driver_idx']] == 3 and ir['SessionState'] == 4 and telem['stint_laps'] > 1:

        # Add current usage to list (and keep previous 5 laps)
        if len(fuel['used_lap_list']) >= 5:
            fuel['used_lap_list'].pop(0)
        fuel['used_lap_list'].append(fuel['used_lap'])

        # Average fuel usage
        if len(fuel['used_lap_list']) > 0:
            total = 0
            for used in fuel['used_lap_list']:
                total = total + used
            fuel['used_lap_avg'] = total / len(fuel['used_lap_list'])

        # Max fuel usage
        if fuel['used_lap'] > fuel['used_lap_max']:
            fuel['used_lap_max'] = fuel['used_lap']

    # Fixed fuel usage
    if gui.Vars.input["fixed_usage"] > 0:
        if state['imperial']:
            fuel['used_lap_fixed'] = gui.Vars.input["fixed_usage"] * 3.78541
        else:
            fuel['used_lap_fixed'] = gui.Vars.input["fixed_usage"]

    # Laps remaining
    try:
        fuel['laps_left'] = fuel['level_current'] / fuel['used_lap']
    except ZeroDivisionError:
        fuel['laps_left'] = 0
    try:
        fuel['laps_left_avg'] = fuel['level_current'] / fuel['used_lap_avg']
    except ZeroDivisionError:
        fuel['laps_left_avg'] = 0
    try:
        fuel['laps_left_max'] = fuel['level_current'] / fuel['used_lap_max']
    except ZeroDivisionError:
        fuel['laps_left_max'] = 0
    try:
        fuel['laps_left_fixed'] = fuel['level_current'] / fuel['used_lap_fixed']
    except ZeroDivisionError:
        fuel['laps_left_fixed'] = 0

    # Required fuel levels
    fuel['level_req'] = ((telem['laps_remaining'] * fuel['used_lap']) - fuel['level_current'])
    if fuel['level_req'] < 0:
        fuel['level_req'] = 0.0
    fuel['level_req_avg'] = ((telem['laps_remaining'] * fuel['used_lap_avg']) - fuel['level_current'])
    if fuel['level_req_avg'] < 0:
        fuel['level_req_avg'] = 0.0
    fuel['level_req_max'] = ((telem['laps_remaining'] * fuel['used_lap_max']) - fuel['level_current'])
    if fuel['level_req_max'] < 0:
        fuel['level_req_max'] = 0.0
    fuel['level_req_fixed'] = ((telem['laps_remaining'] * fuel['used_lap_fixed']) - fuel['level_current'])
    if fuel['level_req_fixed'] < 0:
        fuel['level_req_fixed'] = 0.0

    # Number of pit stops needed
    fuel['stops'] = round(fuel['level_req'] / (fuel['level_full'] * fuel['pct_max']), 1)
    if fuel['stops'] < 0:
        fuel['stops'] = 0.0
    fuel['stops_avg'] = round(fuel['level_req_avg'] / (fuel['level_full'] * fuel['pct_max']), 1)
    if fuel['stops_avg'] < 0:
        fuel['stops_avg'] = 0.0
    fuel['stops_max'] = round(fuel['level_req_max'] / (fuel['level_full'] * fuel['pct_max']), 1)
    if fuel['stops_max'] < 0:
        fuel['stops_max'] = 0.0
    fuel['stops_fixed'] = round(fuel['level_req_fixed'] / (fuel['level_full'] * fuel['pct_max']), 1)
    if fuel['stops_fixed'] < 0:
        fuel['stops_fixed'] = 0.0

    # Pit window opening laps
    if "Race" in session_info("SessionType"):
        if ir['SessionLapsTotal'] > 9999 and telem['lap_times_total_avg'] > 0:
            laps = (ir['SessionTimeTotal'] / telem['lap_times_total_avg'])
        else:
            laps = ir['SessionLapsTotal']
    else:
        laps = gui.Vars.spin["practice_laps"]

    fuel_types = ['', '_avg', '_max', '_fixed']
    for type in fuel_types:
        try:
            total = 0
            while True:
                total = total + (fuel['level_full'] / fuel['used_lap' + type])
                if total > telem['laps_remaining']:
                    fuel['window_lap' + type] = math.ceil(laps - (total - (fuel['level_full'] / fuel['used_lap' + type])) + gui.Vars.spin['extra_laps'])
                    break
        except ZeroDivisionError:
            fuel['window_lap' + type] = 0


def fueling_thread():
    time.sleep(5)
    status_prev = "pitting"
    while state['connected']:
        if gui.Vars.checkboxes["auto_fuel"] and "Qualify" not in session_info("SessionType") and not state['spectator'] and not state['spotter']:
            if "black" not in telem['flag_list']:
                flag_chk = True
            else:
                flag_chk = False
            if ir['CarIdxTrackSurface'][telem['driver_idx']] == 1:
                status = "pitting"
            else:
                status = "driving"
            if status_prev != status:
                if status == "pitting" and flag_chk and ir['OilTemp'] != 77.0:
                    if gui.Vars.combo["auto_fuel_type"] == "Average":
                        if (telem['laps_remaining'] + gui.Vars.spin["extra_laps"]) * fuel['used_lap_avg'] < ir['FuelLevel']:
                            fuel_add = 0.0
                        else:
                            fuel_add = fuel['level_req_avg'] + (fuel['used_lap_avg'] * gui.Vars.spin["extra_laps"])
                    elif gui.Vars.combo["auto_fuel_type"] == "Max":
                        if (telem['laps_remaining'] + gui.Vars.spin["extra_laps"]) * fuel['used_lap_max'] < ir['FuelLevel']:
                            fuel_add = 0.0
                        else:
                            fuel_add = fuel['level_req_max'] + (fuel['used_lap_max'] * gui.Vars.spin["extra_laps"])
                    else:
                        if (telem['laps_remaining'] + gui.Vars.spin["extra_laps"]) * fuel['used_lap_fixed'] < ir['FuelLevel']:
                            fuel_add = 0.0
                        else:
                            fuel_add = fuel['level_req_fixed'] + (fuel['used_lap_fixed'] * gui.Vars.spin["extra_laps"])
                    if len(fuel['used_lap_list']) < 1 or fuel_add > fuel['level_full']:
                        fuel_add = fuel['level_full']
                    if fuel_add + fuel['last_level'] <= ir['FuelLevel']:
                        ir.pit_command(11)
                    elif fuel_add + fuel['last_level'] > ir['FuelLevel']:
                        ir.pit_command(2, int(round(fuel_add, 0)))
                        try:
                            while ir['CarIdxTrackSurface'][telem['driver_idx']] == 1:
                                if fuel_add + fuel['last_level'] <= ir['FuelLevel']:
                                    ir.pit_command(11)
                                    break
                                elif ir['FuelLevel'] >= fuel['level_full']:
                                    break
                                time.sleep(1 / 60)
                        except AttributeError:
                            pass
            status_prev = status
        time.sleep(1 / 20)


def pit_report():
    if fuel['stint_used'] > 0:
        fuel['stint_used_avg'] = fuel['stint_used'] / telem['stint_laps']
        fuel['stint_eco'] = (telem['stint_laps'] * telem['track_length']) / fuel['stint_used']
    else:
        fuel['stint_used_avg'] = 0
        fuel['stint_eco'] = 0
    if ir['LapCompleted'] == 0 and ir['SessionState'] >= 5:
        lap_completed = ir['SessionLapsTotal']
    else:
        lap_completed = ir['LapCompleted']
    separator()
    log("Lap " + str(lap_completed) + " Pit Report")
    log(lang['separator_b'])
    log("Stint: " + str(telem['stint_laps']) + " laps" + ", " + "Avg Time: " + duration(telem['lap_times_stint_avg']) + ", " + "Avg Used: " + volume(fuel['stint_used_avg'], "short") + ", " +
        "Avg Eco: " + economy(fuel['stint_eco']) + ", " + "Total Used: " + volume(fuel['stint_used'], "short"))
    log(lang['separator_a'])
    log("Tire Wear")
    log(lang['separator_b'])
    log("LF: " + percent(ir['LFwearL']) + " " + percent(ir['LFwearM']) + " " + percent(ir['LFwearR']) + "     " + "RF: " + percent(ir['RFwearL']) + " " + percent(ir['RFwearM']) + " " + percent(ir['RFwearR']))
    log("")
    log("LR: " + percent(ir['LRwearL']) + " " + percent(ir['LRwearM']) + " " + percent(ir['LRwearR']) + "     " + "RR: " + percent(ir['RRwearL']) + " " + percent(ir['RRwearM']) + " " + percent(ir['RRwearR']))
    log(lang['separator_a'])
    log("Tire Temp")
    log(lang['separator_b'])
    log("LF: " + temperature(ir['LFtempCL'], "string") + " " + temperature(ir['LFtempCM'], "string") + " " + temperature(ir['LFtempCR'], "string") + "     " +
        "RF: " + temperature(ir['RFtempCL'], "string") + " " + temperature(ir['RFtempCM'], "string") + " " + temperature(ir['RFtempCR'], "string"))
    log("")
    log("LR: " + temperature(ir['LRtempCL'], "string") + " " + temperature(ir['LRtempCM'], "string") + " " + temperature(ir['LRtempCR'], "string") + "     " +
        "RR: " + temperature(ir['RRtempCL'], "string") + " " + temperature(ir['RRtempCM'], "string") + " " + temperature(ir['RRtempCR'], "string"))
    log(lang['separator_a'])
    state['separator'] = True
    telem['stint_laps'] = 0
    fuel['stint_used'] = 0.0
    telem['lap_times_stint'] = []


# Shorten DriverInfo calls
def drv_info(group, subgroup):
    if subgroup == 0:
        return ir['DriverInfo'][group]
    else:
        return ir['DriverInfo'][group][telem['driver_idx']][subgroup]
        # except Exception as ex:
        #    CamIdx = ir['CamCarIdx']
        #    return ir['DriverInfo'][group][CamIdx][subgroup]


# Shorten WeekendInfo calls (and also split string)
def weekend_info(group, n):
    result = ir['WeekendInfo'][group]
    result_spilt = result.split()
    return result_spilt[n]


# Shorten WeekendOptions calls (and also split string)
def weekend_options(group, n):
    result = ir['WeekendInfo']['WeekendOptions'][group]
    result_split = result.split()
    return result_split[n]


# Shorten SessionInfo calls
def session_info(group):
    if state['connected']:
        return ir['SessionInfo']['Sessions'][ir['SessionNum']][group]


# Return sky status
def sky():
    sky_num = ir['Skies']
    skies = "N/A"
    if sky_num == 0:
        skies = "Clear"
    elif sky_num == 1:
        skies = "Partly Cloudy"
    elif sky_num == 2:
        skies = "Mostly Cloudy"
    elif sky_num == 3:
        skies = "Overcast"
    return skies


# Func to not double up on separators because it bothered me
def separator():
    if not state['separator']:
        log(lang['separator_a'])


# Log session info
def session():
    separator()
    log(session_info("SessionType"))
    log(lang['separator_b'])
    log("Skies: " + sky() + ", " + "Air: " + temperature(ir['AirTemp'], "string") + ", " + "Surface: " + temperature(ir['TrackTempCrew'], "string") + ", " + "Wind: " + wind() + " @ " + speed(ir['WindVel']) + ", " +
        "Humidity: " + percent(ir['RelativeHumidity']) + ", " + "Pressure: " + pressure(ir['AirPressure']) + ", " + "Density: " + density(ir['AirDensity']))
    log(lang['separator_a'])
    telem['last_air_temp'] = ir['AirTemp']
    telem['last_track_temp'] = ir['TrackTempCrew']
    telem['laps_completed'] = 0
    telem['laps_remaining'] = 0
    telem['session'] = session_info("SessionType")
    fuel['used_lap_avg'] = 0.0
    fuel['used_lap_max'] = 0.0
    fuel['used_lap_list'] = []
    state['reset_laps'] = False
    fuel['pct_max'] = drv_info("DriverCarMaxFuelPct", 0)
    state['separator'] = True


# Environment temperature checking and alerts
def check_temps():
    # Air Temp
    if ((ir['AirTemp'] * 1.8) + 32) > ((telem['last_air_temp'] * 1.8) + 32) + 1 or ((ir['AirTemp'] * 1.8) + 32) < ((telem['last_air_temp'] * 1.8) + 32) - 1:
        if ir['AirTemp'] > telem['last_air_temp']:
            speech = threading.Thread(target=speech_thread, args=("air temp has increased to " + str(round(temperature(ir['AirTemp'], "number"))) + " degrees",))
            speech.start()
        else:
            speech = threading.Thread(target=speech_thread, args=("air temp has decreased to " + str(round(temperature(ir['AirTemp'], "number"))) + " degrees",))
            speech.start()
        separator()
        log("Ambient: " + temperature(ir['AirTemp'], "string"))
        log(lang['separator_a'])
        state['separator'] = True
        telem['last_air_temp'] = ir['AirTemp']

    # Track temp
    if ((ir['TrackTempCrew'] * 1.8) + 32) > ((telem['last_track_temp'] * 1.8) + 32) + 3 or ((ir['TrackTempCrew'] * 1.8) + 32) < ((telem['last_track_temp'] * 1.8) + 32) - 3:
        if ir['TrackTempCrew'] > telem['last_track_temp']:
            speech = threading.Thread(target=speech_thread, args=("track temp has increased to " + str(round(temperature(ir['TrackTempCrew'], "number"))) + " degrees",))
            speech.start()
        else:
            speech = threading.Thread(target=speech_thread, args=("track temp has decreased to " + str(round(temperature(ir['TrackTempCrew'], "number"))) + " degrees",))
            speech.start()
        separator()
        log("Surface: " + temperature(ir['TrackTempCrew'], "string"))
        log(lang['separator_a'])
        state['separator'] = True
        telem['last_track_temp'] = ir['TrackTempCrew']


# Engine warning tracking and alerts
def engine_warnings():
    # Oil
    if "oil_temp_warning" in telem['engine_list']:
        if not telem['oil_warning_prev'] and telem['oil_temp_warning'] == 999.0:
            telem['oil_temp_warning'] = ir['OilTemp']
        telem['oil_warning_prev'] = True
    else:
        telem['oil_warning_prev'] = False
    if state['imperial']:
        oil_threshold = (gui.Vars.input["oil_threshold"] - 32) * (5 / 9)
    else:
        oil_threshold = gui.Vars.input["oil_threshold"]
    if telem['oil_temp_warning'] >= oil_threshold:
        if ir['OilTemp'] >= telem['oil_temp_warning']:
            telem['oil_trigger'] = True
        if ir['OilTemp'] <= (telem['oil_temp_warning'] - 5):
            if telem['oil_warned']:
                threading.Thread(target=speech_thread, args=("oil temp has fallen to " + str(round(temperature(ir['OilTemp'], "number"))) + " degrees",)).start()
                telem['oil_warned'] = False
    elif telem['oil_temp_warning'] < oil_threshold:
        if ir['OilTemp'] >= oil_threshold:
            telem['oil_trigger'] = True
        if ir['OilTemp'] <= (oil_threshold - 5):
            if telem['oil_warned']:
                threading.Thread(target=speech_thread, args=("oil temp has fallen to " + str(round(temperature(ir['OilTemp'], "number"))) + " degrees",)).start()
                telem['oil_warned'] = False
    if telem['oil_trigger'] and not telem['oil_warned']:
        threading.Thread(target=speech_thread, args=("oil temp has risen to " + str(round(temperature(ir['OilTemp'], "number"))) + " degrees",)).start()
        telem['oil_warned'] = True
    telem['oil_trigger'] = False

    # Water
    if "water_temp_warning" in telem['engine_list']:
        if not telem['water_warning_prev'] and telem['water_temp_warning'] == 999.0:
            telem['water_temp_warning'] = ir['WaterTemp']
        telem['water_warning_prev'] = True
    else:
        telem['water_warning_prev'] = False
    if state['imperial']:
        water_threshold = (gui.Vars.input["water_threshold"] - 32) * (5 / 9)
    else:
        water_threshold = gui.Vars.input["water_threshold"]
    if telem['water_temp_warning'] >= water_threshold:
        if ir['WaterTemp'] >= telem['water_temp_warning']:
            telem['water_trigger'] = True
        if ir['WaterTemp'] <= (telem['water_temp_warning'] - 5):
            if telem['water_warned']:
                threading.Thread(target=speech_thread, args=("water temp has fallen to " + str(round(temperature(ir['WaterTemp'], "number"))) + " degrees",)).start()
                telem['water_warned'] = False
    elif telem['water_temp_warning'] < water_threshold:
        if ir['WaterTemp'] >= water_threshold:
            telem['water_trigger'] = True
        if ir['WaterTemp'] <= (water_threshold - 5):
            if telem['water_warned']:
                threading.Thread(target=speech_thread, args=("water temp has fallen to " + str(round(temperature(ir['WaterTemp'], "number"))) + " degrees",)).start()
                telem['water_warned'] = False
    if telem['water_trigger'] and not telem['water_warned']:
        threading.Thread(target=speech_thread, args=("water temp has risen to " + str(round(temperature(ir['WaterTemp'], "number"))) + " degrees",)).start()
        telem['water_warned'] = True
    telem['water_trigger'] = False


# Variable actions to run on connect
def init_vars():
    # Detect user's driver id and determine if they are a spectator or spotter
    uid = drv_info("DriverUserID", 0)
    for idx in range(64, -2, -1):
        try:
            cid = ir['DriverInfo']['Drivers'][idx]['UserID']
            if cid == uid:
                telem['driver_idx'] = idx
                if drv_info("Drivers", "IsSpectator") == 1:
                    state['spectator'] = True
                break
            elif idx == -1:
                telem['driver_idx'] = drv_info("DriverCarIdx", 0)
                state['spotter'] = True
        except IndexError:
            pass

    if ir['DisplayUnits'] == 0:
        state['imperial'] = True
    fuel['level_full'] = drv_info("DriverCarFuelMaxLtr", 0)
    fuel['pct_max'] = drv_info("DriverCarMaxFuelPct", 0)
    telem['lap_next'] = 1
    telem['timer_start'] = time.perf_counter()
    track_length = ir['WeekendInfo']['TrackLength']
    track_length_spl = track_length.split()
    telem['track_length'] = float(track_length_spl[0])
    telem['session'] = session_info("SessionType")


# Variable actions to run on disconnect
def deinit_vars():
    # Reset all state variables
    state_vars = list(state.keys())
    for var in state_vars:
        if isinstance(state[var], bool):
            if var == "separator":
                pass
            else:
                state[var] = False

    # Reset all fuel variables
    fuel_vars = list(fuel.keys())
    for var in fuel_vars:
        if isinstance(fuel[var], int):
            fuel[var] = 0
        elif isinstance(fuel[var], float):
            fuel[var] = 0.0
        elif isinstance(fuel[var], list):
            fuel[var] = []

    # Reset all telemetry variables
    telem_vars = list(telem.keys())
    for var in telem_vars:
        if isinstance(telem[var], int):
            if "x" in str(var):
                telem[var] = 0x00000000
            else:
                telem[var] = 0
        elif isinstance(telem[var], float):
            telem[var] = 0.0
        elif isinstance(telem[var], list):
            telem[var] = []
        elif isinstance(telem[var], bool):
            telem[var] = False
        elif isinstance(telem[var], str):
            telem[var] = ""
    telem['oil_temp_warning'] = 999.0
    telem['water_temp_warning'] = 999.0


# Variable actions to reset while connected
def reset_vars(name):
    # State
    if name == ("state", "all"):
        state['lap_trigger'] = False
        state['reset_laps'] = False

    # Lang
    if name == ("lang", "all"):
        pass

    # Fuel
    if name == ("fuel", "all"):
        fuel['eco'] = 0.0
        fuel['eco_req'] = 0.0
        fuel['laps_left'] = 0.0
        fuel['laps_left_avg'] = 0.0
        fuel['laps_left_max'] = 0.0
        fuel['laps_left_fixed'] = 0.0
        fuel['last_level'] = 0.0
        fuel['last_level_pit'] = 0.0
        fuel['level_current'] = 0.0
        fuel['level_full'] = drv_info("DriverCarFuelMaxLtr", 0)
        fuel['level_req'] = 0.0
        fuel['level_req_avg'] = 0.0
        fuel['level_req_max'] = 0.0
        fuel['level_req_fixed'] = 0.0
        fuel['pct_current'] = 0.0
        fuel['pct_max'] = drv_info("DriverCarMaxFuelPct", 0)
        fuel['stint_eco'] = 0.0
        fuel['stint_used'] = 0.0
        fuel['stint_used_avg'] = 0.0
        fuel['stops'] = 0
        fuel['stops_avg'] = 0
        fuel['stops_max'] = 0
        fuel['stops_fixed'] = 0
        fuel['used_lap'] = 0.0
        fuel['used_lap_avg'] = 0.0
        fuel['used_lap_max'] = 0.0
        fuel['used_lap_list'] = []
        fuel['used_lap_req'] = 0.0
        fuel['window_lap'] = 0
        fuel['window_lap_avg'] = 0
        fuel['window_lap_max'] = 0
        fuel['window_lap_fixed'] = 0

    # Telem
    if name == ("telem", "all"):
        telem['flag_hex'] = 0x00000000
        telem['flag_list'] = []
        telem['engine_hex'] = 0x00000000
        telem['engine_list'] = []
        telem['lap_next'] = 1
        telem['lap_time_prev'] = 0.0
        telem['lap_times_stint'] = []
        telem['lap_times_stint_avg'] = 0.0
        telem['lap_times_total'] = []
        telem['lap_times_total_avg'] = 0.0
        telem['laps_completed'] = 0
        telem['oil_warned'] = False
        telem['stint_laps'] = 0
        telem['timer_start'] = time.perf_counter()
        telem['water_warned'] = False


# Check iRacing connection status and do actions
def check_iracing():
    try:
        if not state['connected'] and ir.startup() and ir.is_initialized and ir.is_connected:
            # Set connection status
            state['connected'] = True

            # Start connected-only threads
            threading.Thread(target=fueling_thread, daemon=True).start()
            threading.Thread(target=warnings_thread, daemon=True).start()

            # Connected alert
            separator()
            log('iRacing Connected')
            log(lang['separator_a'])
            state['separator'] = True
            speech = threading.Thread(target=speech_thread, args=("Fuel companion connected",))
            speech.start()
            # time.sleep(3)

            # Call init variable actions
            init_vars()

            # Print weekend and session info
            separator()
            log("Weekend")
            log(lang['separator_b'])
            log("Track: " + weekend_info("TrackName", 0) + ", " + "Car: " + drv_info("Drivers", "CarPath") + ", " + "Length: " + distance(telem['track_length'], "km") + ", " +
                "Date: " + weekend_options("Date", 0) + " " + weekend_options("TimeOfDay", 0) + weekend_options("TimeOfDay", 1) + ", " + "Rubber: " + session_info("SessionTrackRubberState") + ", " + "Max Fuel: " + percent(fuel['pct_max']))
            state['separator'] = False
            session()

            # Needed to "reset" keyboard module for some reason
            time.sleep(1)
            keyboard.write("")
        elif state['connected'] and not (ir.is_initialized and ir.is_connected):
            # Disconnected alert
            separator()
            log('iRacing Disconnected')
            log(lang['separator_a'])
            state['separator'] = True

            # Shut down irsdk
            ir.shutdown()

            # Call deinit variable actions
            deinit_vars()
    except ConnectionResetError:
        pass


# Check for lap complete and do actions
def lap_actions():
    # Detect lap change
    if ir['LapCompleted'] < telem['lap_next'] or ir['LapCompleted'] > telem['lap_next'] + 1:
        telem['lap_next'] = ir['LapCompleted'] + 1
    elif ir['LapCompleted'] == telem['lap_next']:
        telem['lap_next'] = telem['lap_next'] + 1
        state['lap_trigger'] = True

    # Trigger actions on lap change
    if state['lap_trigger']:
        time.sleep(1)
        ir.freeze_var_buffer_latest()
        # Set previous lap time
        if ir['LapLastLapTime'] <= 0 or ir['LapLastLapTime'] == telem['lap_time_prev']:
            telem['lap_time_prev'] = time.perf_counter() - telem['timer_start']
        else:
            telem['lap_time_prev'] = ir['LapLastLapTime']
        telem['timer_start'] = time.perf_counter()

        # Set average lap times
        if ir['LapCompleted'] > 0:
            # Total
            telem['lap_times_total'].append(telem['lap_time_prev'])
            total = 0
            for lap in telem['lap_times_total']:
                total = total + lap
                telem['lap_times_total_avg'] = total / len(telem['lap_times_total'])

            # Stint
            telem['lap_times_stint'].append(telem['lap_time_prev'])
            total = 0
            for lap in telem['lap_times_stint']:
                total = total + lap
            telem['lap_times_stint_avg'] = total / len(telem['lap_times_stint'])

        # Set completed lap amount
        if "Qualify" not in session_info("SessionType") or "Race" not in session_info("SessionType"):
            telem['laps_completed'] = telem['laps_completed'] + 1
        else:
            telem['laps_completed'] = ir['LapCompleted']

        # Determine laps remaining
        if ir['SessionLapsRemain'] > 9999 and telem['lap_times_total_avg'] > 0:
            telem['laps_remaining'] = math.ceil(ir['SessionTimeRemain'] / telem['lap_times_total_avg'])
        elif ir['SessionLapsRemain'] > 9999 and telem['lap_times_total_avg'] <= 0:
            telem['laps_remaining'] = math.ceil(ir['SessionTimeRemain'] / (telem['track_length'] / (100 / 3600)))
        elif (ir['SessionLapsRemain'] + 1) < 0:
            telem['laps_remaining'] = 0
        elif "Qualify" not in session_info("SessionType") and "Race" not in session_info("SessionType"):
            telem['laps_remaining'] = gui.Vars.spin["practice_laps"] - telem['laps_completed']
        else:
            telem['laps_remaining'] = ir['SessionLapsRemain'] + 1

        # Set laps in current stint
        telem['stint_laps'] = telem['stint_laps'] + 1

        # Call fuel calculations
        try:
            fuel_calc()
        except ZeroDivisionError:
            pass

        # Do end of lap updates/alerts
        if ir['CarIdxPaceLine'][telem['driver_idx']] == -1 and telem['surface'] == 3 and ir['SessionState'] == 4 and telem['stint_laps'] > 0:
            # TTS callouts
            if gui.Vars.checkboxes["tts_fuel"] and session_info("SessionType") != "Lone Qualify":
                threading.Thread(target=speech_thread, args=(str(round(fuel['laps_left'], 2)) + " laps, " + volume(fuel['used_lap'], "long"),)).start()
            # Text callouts
            if gui.Vars.checkboxes["txt_fuel"] and "Qualify" not in session_info("SessionType"):
                time.sleep(0.50)
                ir.chat_command(1)
                time.sleep(0.1)
                keyboard.write("## Previous lap - " + str(round(fuel['laps_left'], 2)) + " laps, " + volume(fuel['used_lap'], "short") + ", " + economy(fuel['eco']) + ", " +
                               volume(fuel['level_req'], "short") + "(" + str(fuel['stops']) + ", " + str(fuel['window_lap']) + ") extra ##")
                time.sleep(0.1)
                keyboard.send('enter')
                time.sleep(0.1)
                ir.chat_command(3)

        # Write previous lap info to logs
        if ir['SessionState'] < 6:
            if "Race" not in session_info("SessionType"):
                log("Lap " + str(ir['LapCompleted']) + " [Time: " + duration(telem['lap_time_prev']) + " | Laps: " + str(round(fuel['laps_left'], 2)) + " | Used: " + volume(fuel['used_lap'], "short") + " | Eco: " + economy(fuel['eco']) + "]")
            else:
                log("Lap " + str(ir['LapCompleted']) + " [Time: " + duration(telem['lap_time_prev']) + " | Laps: " + str(round(fuel['laps_left'], 2)) + " | Used: " + volume(fuel['used_lap'], "short") +
                    " | Usage Req: " + volume(fuel['used_lap_req'], "short") + " | Eco: " + economy(fuel['eco']) + " | Eco Req: " + economy(fuel['eco_req']) + " | Level Req: " + volume(fuel['level_req'], "short") + "]")
            state['separator'] = False

        # Set variables
        fuel['last_level'] = fuel['level_current']
        state['lap_trigger'] = False
        ir.unfreeze_var_buffer_latest()


# Main loop (run in thread because of GUI weirdness)
def main():
    ir.freeze_var_buffer_latest()

    # Detect session change or reset
    if math.floor(ir['SessionTime']) == 0.0:
        time.sleep(1)
        if telem['session'] != session_info("SessionType"):
            session()
        reset_vars("all")

    # Detect units continuously
    if ir['DisplayUnits'] == 0:
        state['imperial'] = True

    # Update live fuel vars
    if ir['FuelLevel'] == 0.0 and fuel['level_current'] != 0.0:
        fuel['level_current'] = fuel['level_current']
    else:
        fuel['level_current'] = ir['FuelLevel']
    fuel['pct_current'] = ir['FuelLevelPct']

    # Update live telem vars
    telem['flag_hex'] = ir['SessionFlags']
    telem['engine_hex'] = ir['EngineWarnings']

    # Check engine warnings
    if gui.Vars.checkboxes["engine_warnings"]:
        engine_warnings()

    # Check air and track temperatures
    if gui.Vars.checkboxes["temp_updates"]:
        if ir['SessionTime'] > 30.0:
            check_temps()

    # Practice race fuel percent and resetting
    if "Qualify" not in session_info("SessionType") and "Race" not in session_info("SessionType"):
        # If max fuel is default, use custom setting
        if drv_info("DriverCarMaxFuelPct", 0) == 1:
            fuel['pct_max'] = gui.Vars.spin["practice_fuel_percent"] / 100

        # Roundabout way of detecting when driver has towed, in order to reset the practice race
        if ir['OilTemp'] == 77.0 and state['reset_laps']:
            reset_vars("all")
            state['reset_laps'] = False
        elif ir['OilTemp'] != 77.0:
            state['reset_laps'] = True

    ir.unfreeze_var_buffer_latest()

    # Lap detect and actions
    lap_actions()

    # Pit report
    if ir['CarIdxTrackSurface'][telem['driver_idx']] != telem['surface'] and ir['CarIdxTrackSurface'][telem['driver_idx']] == 1 or ir['CarIdxTrackSurface'][telem['driver_idx']] != telem['surface'] and ir['CarIdxTrackSurface'][telem['driver_idx']] == -1:
        fuel['stint_used'] = fuel['last_level_pit'] - fuel['level_current']
        if fuel['stint_used'] <= 0:
            fuel['stint_used'] = fuel['last_level_pit'] - fuel['last_level']
        if telem['stint_laps'] > 0:
            if ir['SessionState'] <= 4 or ir['SessionState'] >= 5 and not ir['IsOnTrack']:
                pit_report()

    if telem['surface'] == 1 and ir['CarIdxTrackSurface'][telem['driver_idx']] != 1 or telem['surface'] == -1 and ir['CarIdxTrackSurface'][telem['driver_idx']] != -1:
        fuel['last_level_pit'] = ir['FuelLevel']

    telem['surface'] = ir['CarIdxTrackSurface'][telem['driver_idx']]


def init():
    time.sleep(1)
    log("iR Fuel Companion " + state['version'])
    log(lang['separator_a'])

    # Check for updates
    if gui.Vars.checkboxes["check_updates"]:
        try:
            with urllib.request.urlopen('https://www.renovamenia.com/files/iracing/other/iR_Fuel_Companion/version.txt') as file:
                server_version = file.read().decode('utf-8').strip("v").split('.')
                local_version = state['version'].strip("v").split('.')
                if local_version[0] < server_version[0]:
                    available = True
                elif local_version[1] < server_version[1]:
                    available = True
                elif local_version[2] < server_version[2]:
                    available = True
                else:
                    available = False
                if available:
                    threading.Thread(target=speech_thread, args=("Update v" + server_version[0] + "." + server_version[1] + "." + server_version[2] + " available!",)).start()
                    log("Update v" + server_version[0] + "." + server_version[1] + "." + server_version[2] + " available! https://github.com/janewsome63/iR-Fuel-Companion/releases")
                    log(lang['separator_a'])
        except urllib.error.URLError as error:
            log("Update checking failed, cannot connect to update server! " + str(error))
            log(lang['separator_a'])

    try:
        # Check connection and start (or not) loop
        while True:
            check_iracing()
            if state['connected']:
                main()
            # Data read delay (min 1/60)
            time.sleep(1 / 15)
    except KeyboardInterrupt:
        pass


Date = datetime.now()
DateStr = Date.strftime("%Y-%m-%d")

# Create user settings folder
gui.Vars.user_dir = os.path.expanduser("~") + '\\AppData\\Local\\iR Fuel Companion'
if not os.path.exists(gui.Vars.user_dir):
    os.makedirs(gui.Vars.user_dir)

# Logging
# Create logs folder
if not os.path.exists(gui.Vars.user_dir + '\\logs'):
    os.makedirs(gui.Vars.user_dir + '\\logs')

# Create a logger
logger = logging.getLogger(__name__)

# Create a file handler
file_handler = logging.FileHandler(gui.Vars.user_dir + '\\logs\\' + DateStr + '.txt')

# Add the file handler to the logger
logger.addHandler(file_handler)

# Set the logging level
logger.setLevel(logging.INFO)


# Define the fuction to log to both stdout and file
def log(text):
    logger.info(text)
    print(text)


if __name__ == '__main__':
    # Initializing ir and State
    ir = irsdk.IRSDK()
    if not os.path.exists(gui.Vars.user_dir + '\\settings.ini'):
        gui.set_config()
    read_config()
    tts = wincl.Dispatch("SAPI.SpVoice")
    # threading.Thread(target=keybind.gamepad, daemon=True).start()
    threading.Thread(target=keybind.keys, daemon=True).start()
    threading.Thread(target=controls_thread, daemon=True).start()
    threading.Thread(target=binding_thread, daemon=True).start()
    threading.Thread(target=init, daemon=True).start()

    gui.main(state['version'])
