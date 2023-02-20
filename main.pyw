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


# Random variables and functions for main thread
class State:
    count = 1
    ir_connected = False
    no_connection = "no eye racing connection"
    laps_completed = 0
    metric = True
    log_sep = True
    reset_laps = 0
    sep_1 = "=" * 138
    sep_2 = "-" * 138
    spectator = False
    spotter = False
    surface = -1
    trigger = False
    version = "v0.2.6"


# Fuel variables
class Fuel:
    eco = 0.0
    eco_req = 0.0
    laps_left = 0.0
    last_level = 0.0
    last_pit_level = 0.0
    level = 0.0
    level_full = 0.0
    level_req = 0.0
    level_req_avg = 0.0
    level_req_max = 0.0
    level_req_fixed = 0.0
    max_pct = 0.0
    pct = 0.0
    stint_eco = 0.0
    stint_used = 0.0
    stint_used_avg = 0.0
    stops = 0
    stops_avg = 0
    stops_max = 0
    stops_fixed = 0
    used_lap = 0.0
    used_lap_avg = 0.0
    used_lap_max = 0.0
    used_lap_fixed = 0.0
    used_lap_list = []
    used_lap_req = 0.0


# Other iR telemetry variables
class Telem:
    driver_idx = 0
    flag = 0x00000000
    flag_list = []
    engine = 0x00000000
    engine_list = []
    lap_distance = 0
    lap_time_list = []
    laps_completed = 0
    laps_remaining = 0
    last_ttemp = 0.0
    last_atemp = 0.0
    location = 1
    oil_temp_warning = 999.0
    oil_trigger = False
    oil_warned = False
    oil_warning_prev = False
    session = 0
    stint_laps = 0
    water_temp_warning = 999.0
    water_trigger = False
    water_warned = False
    water_warning_prev = False


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

# Return game unit type
def detect_units():
    if ir['DisplayUnits'] == 1:
        State.metric = True
    elif ir['DisplayUnits'] == 0:
        State.metric = False


# Return converted temperature
def temperature(value, style):
    if State.metric:
        if style == "string":
            return str(round(value, 2)) + "c"
        elif style == "number":
            return round(value, 2)
    else:
        if style == "string":
            return str(round((value * 1.8) + 32, 2)) + "f"
        if style == "number":
            return round((value * 1.8) + 32, 2)


# Return converted speed
def speed(value):
    if State.metric:
        return str(round(value * 3.6, 1)) + "kph"
    else:
        return str(round(value * 2.2369362920544025, 1)) + "mph"


# Return converted pressure
def pressure(value):
    if State.metric:
        return str(round(value * 3.38639, 1)) + "kpa"
    else:
        return str(round(value, 1)) + "hg"


# Return converted density
def density(value):
    if State.metric:
        return str(round(value, 2)) + "kg/m^3"
    else:
        return str(round(value * 0.062427960576145, 2)) + "lb/ft^3"


# Return converted distance
def distance(value, magnitude):
    if State.metric:
        if magnitude == "m":
            return str(round(value * 0.001, 2)) + "km"
        elif magnitude == "km":
            return str(round(value, 2)) + "km"
    else:
        if magnitude == "m":
            return str(round(value * 0.000621371, 2)) + "mi"
        elif magnitude == "km":
            return str(round(value * 0.621371, 2)) + "mi"


# Return converted volume
def volume(value, suffix):
    if State.metric:
        if suffix == "short":
            return str(round(value, 3)) + "l"
        elif suffix == "long":
            return str(round(value, 3)) + " liters"
    else:
        if suffix == "short":
            return str(round(value * 0.264172, 3)) + "gal"
        elif suffix == "long":
            return str(round(value * 0.264172, 3)) + " gallons"


# Return converted economy
def economy(value):
    if State.metric:
        return str(round(value, 2)) + "km/l"
    elif not State.metric:
        return str(round(value * 2.352145833, 2)) + "mpg"


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


def controls_set(bind, event):
    if keybind.Vars.button == "esc":
        getattr(gui.Binds, "keys")[bind] = ""
        gui.event(event, "")
    elif keybind.Vars.button != "None":
        getattr(gui.Binds, "keys")[bind] = keybind.Vars.button
        controls_name(bind)
        gui.event(event, "")


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


def controls_thread():
    while True:
        # Pause after binding to prevent immediate trigger
        while gui.Binds.pause_count > 0:
            gui.Binds.pause_count = gui.Binds.pause_count - 1
            time.sleep(0.5)
        # Actions for all triggered keybinds
        if gui.Binds.keys["auto_fuel"] == keybind.Vars.button:
            time.sleep(0.25)
            if gui.Vars.checkboxes["auto_fuel"]:
                gui.event('check-auto_fuel', 0)
                threading.Thread(target=speech_thread, args=("auto fuel disabled",)).start()
            elif not gui.Vars.checkboxes["auto_fuel"]:
                gui.event('check-auto_fuel', 1)
                threading.Thread(target=speech_thread, args=("auto fuel enabled",)).start()
            time.sleep(0.75)
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
        if gui.Binds.keys["auto_fuel_average"] == keybind.Vars.button:
            time.sleep(0.25)
            gui.event('combo-auto_fuel_type', "Average")
            threading.Thread(target=speech_thread, args=("using average usage for auto fuel",)).start()
            time.sleep(0.75)
        if gui.Binds.keys["auto_fuel_max"] == keybind.Vars.button:
            time.sleep(0.25)
            gui.event('combo-auto_fuel_type', "Max")
            threading.Thread(target=speech_thread, args=("using max usage for auto fuel",)).start()
            time.sleep(0.75)
        if gui.Binds.keys["auto_fuel_fixed"] == keybind.Vars.button:
            time.sleep(0.25)
            gui.event('combo-auto_fuel_type', "Fixed")
            threading.Thread(target=speech_thread, args=("using fixed usage for auto fuel",)).start()
            time.sleep(0.75)
        if gui.Binds.keys["set_required"] == keybind.Vars.button:
            time.sleep(0.25)
            if State.ir_connected:
                if gui.Vars.combo["auto_fuel_type"] == "Average":
                    if (Telem.laps_remaining + gui.Vars.spin["extra_laps"]) * Fuel.used_lap_avg < ir['FuelLevel']:
                        fuel_add = 0.0
                    else:
                        fuel_add = Fuel.level_req_avg + (Fuel.used_lap_avg * gui.Vars.spin["extra_laps"])
                elif gui.Vars.combo["auto_fuel_type"] == "Max":
                    if (Telem.laps_remaining + gui.Vars.spin["extra_laps"]) * Fuel.used_lap_max < ir['FuelLevel']:
                        fuel_add = 0.0
                    else:
                        fuel_add = Fuel.level_req_max + (Fuel.used_lap_max * gui.Vars.spin["extra_laps"])
                else:
                    if (Telem.laps_remaining + gui.Vars.spin["extra_laps"]) * Fuel.used_lap_fixed < ir['FuelLevel']:
                        fuel_add = 0.0
                    else:
                        fuel_add = Fuel.level_req_fixed + (Fuel.used_lap_fixed * gui.Vars.spin["extra_laps"])
                if fuel_add + Fuel.last_level <= ir['FuelLevel']:
                    ir.pit_command(11)
                if fuel_add + Fuel.last_level > ir['FuelLevel']:
                    ir.pit_command(2, int(round(fuel_add, 0)))
                speech = threading.Thread(target=speech_thread, args=("fuel set",))
                speech.start()
            else:
                speech = threading.Thread(target=speech_thread, args=(State.no_connection,))
                speech.start()
            time.sleep(0.75)
        if gui.Binds.keys["tts_fuel"] == keybind.Vars.button:
            time.sleep(0.25)
            if gui.Vars.checkboxes["tts_fuel"]:
                gui.event('check-tts_fuel', 0)
                threading.Thread(target=speech_thread, args=("speech fuel updates disabled",)).start()
            elif not gui.Vars.checkboxes["tts_fuel"]:
                gui.event('check-tts_fuel', 1)
                threading.Thread(target=speech_thread, args=("speech fuel updates enabled",)).start()
            time.sleep(0.75)
        if gui.Binds.keys["txt_fuel"] == keybind.Vars.button:
            time.sleep(0.25)
            if gui.Vars.checkboxes["txt_fuel"]:
                gui.event('check-txt_fuel', 0)
                threading.Thread(target=speech_thread, args=("text fuel updates disabled",)).start()
            elif not gui.Vars.checkboxes["txt_fuel"]:
                gui.event('check-txt_fuel', 1)
                threading.Thread(target=speech_thread, args=("text fuel updates enabled",)).start()
            time.sleep(0.75)
        if gui.Binds.keys["temp_updates"] == keybind.Vars.button:
            time.sleep(0.25)
            if gui.Vars.checkboxes["temp_updates"]:
                gui.event('check-temp_updates', 0)
                threading.Thread(target=speech_thread, args=("temperature updates disabled",)).start()
            elif not gui.Vars.checkboxes["temp_updates"]:
                gui.event('check-temp_updates', 1)
                threading.Thread(target=speech_thread, args=("temperature updates enabled",)).start()
            time.sleep(0.75)
        if gui.Binds.keys["temp_report"] == keybind.Vars.button:
            time.sleep(0.25)
            if State.ir_connected:
                threading.Thread(target=speech_thread, args=("air temp is " + str(round(temperature(ir['AirTemp'], "number"))) + " and track temp is " + str(round(temperature(ir['TrackTempCrew'], "number"))),)).start()
            else:
                threading.Thread(target=speech_thread, args=(State.no_connection,)).start()
            time.sleep(0.75)
        if gui.Binds.keys["previous_usage"] == keybind.Vars.button:
            time.sleep(0.25)
            if State.ir_connected:
                ir.chat_command(1)
                time.sleep(0.05)
                keyboard.write("## Previous lap - " + str(round(Fuel.laps_left, 2)) + " laps, " + volume(Fuel.used_lap, "short") + ", " + economy(Fuel.eco) + ", " + volume(Fuel.level_req, "short") + "(" + str(Fuel.stops) + ") extra ##")
                time.sleep(0.05)
                keyboard.send('enter')
                time.sleep(0.05)
                ir.chat_command(3)
            else:
                threading.Thread(target=speech_thread, args=(State.no_connection,)).start()
            time.sleep(0.75)
        if gui.Binds.keys["required_usage"] == keybind.Vars.button:
            time.sleep(0.25)
            if State.ir_connected:
                ir.chat_command(1)
                time.sleep(0.05)
                if gui.Vars.input["fixed_usage"] > 0.0:
                    keyboard.write("## Required - " + str(Telem.laps_remaining) + " laps, " + volume(Fuel.used_lap_req, "short") + ", " + economy(Fuel.eco_req) + ", " + volume(Fuel.level_req_avg, "short") + "(" + str(Fuel.stops_avg) + ") avg, " +
                                   volume(Fuel.level_req_max, "short") + "(" + str(Fuel.stops_max) + ") max, " + volume(Fuel.level_req_fixed, "short") + "(" + str(Fuel.stops_fixed) + ") fixed ##")
                else:
                    keyboard.write("## Required - " + str(Telem.laps_remaining) + " laps, " + volume(Fuel.used_lap_req, "short") + ", " + economy(Fuel.eco_req) + ", " + volume(Fuel.level_req_avg, "short") + "(" + str(Fuel.stops_avg) + ") avg, " +
                                   volume(Fuel.level_req_max, "short") + "(" + str(Fuel.stops_max) + ") max ##")
                time.sleep(0.05)
                keyboard.send('enter')
                time.sleep(0.05)
                ir.chat_command(3)
            else:
                threading.Thread(target=speech_thread, args=(State.no_connection,)).start()
            time.sleep(0.75)
        time.sleep(1 / 20)


def binding_thread():
    while True:
        if not gui.Binds.binding:
            time.sleep(1 / 2)
        else:
            while gui.Binds.binding:
                if gui.Binds.recording["auto_fuel"]:
                    controls_set('auto_fuel', 'bind-auto_fuel')
                elif gui.Binds.recording["auto_fuel_cycle"]:
                    controls_set('auto_fuel_cycle', 'bind-auto_fuel_cycle')
                elif gui.Binds.recording["auto_fuel_average"]:
                    controls_set('auto_fuel_average', 'bind-auto_fuel_average')
                elif gui.Binds.recording["auto_fuel_max"]:
                    controls_set('auto_fuel_max', 'bind-auto_fuel_max')
                elif gui.Binds.recording["auto_fuel_fixed"]:
                    controls_set('auto_fuel_fixed', 'bind-auto_fuel_fixed')
                elif gui.Binds.recording["set_required"]:
                    controls_set('set_required', 'bind-set_required')
                elif gui.Binds.recording["tts_fuel"]:
                    controls_set('tts_fuel', 'bind-tts_fuel')
                elif gui.Binds.recording["txt_fuel"]:
                    controls_set('txt_fuel', 'bind-txt_fuel')
                elif gui.Binds.recording["temp_updates"]:
                    controls_set('temp_updates', 'bind-temp_updates')
                elif gui.Binds.recording["temp_report"]:
                    controls_set('temp_report', 'bind-temp_report')
                elif gui.Binds.recording["previous_usage"]:
                    controls_set('previous_usage', 'bind-previous_usage')
                elif gui.Binds.recording["required_usage"]:
                    controls_set('required_usage', 'bind-required_usage')
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


def speech_thread(text):
    pythoncom.CoInitialize()
    speech = wincl.Dispatch("SAPI.SpVoice")
    speech.Speak(text)


# def engine_compare(value, name):
#     if Telem.engine & value == value:
#         Telem.engine_list.append(name)


# Return driver flag
def warnings_thread():
    flag_hex = {
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
    engine_hex = {
        "water_temp_warning": 0x01,
        "fuel_pressure_warning": 0x02,
        "oil_pressure_warning": 0x04,
        "engine_stalled": 0x08,
        "pit_speed_limiter": 0x10,
        "rev_limiter_active": 0x20,
        "oil_temp_warning": 0x40,
    }

    def flag_compare(name):
        if Telem.flag & flag_hex[name] == flag_hex[name]:
            Telem.flag_list.append(name)

    def engine_compare(name):
        if Telem.engine & engine_hex[name] == engine_hex[name]:
            Telem.engine_list.append(name)

    while State.ir_connected:
        Telem.flag_list = []
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

        Telem.engine_list = []
        engine_compare("water_temp_warning")
        engine_compare("fuel_pressure_warning")
        engine_compare("oil_pressure_warning")
        engine_compare("engine_stalled")
        engine_compare("pit_speed_limiter")
        engine_compare("rev_limiter_active")
        engine_compare("oil_temp_warning")
        time.sleep(1)


def fuel_calc_init():
    Fuel.level = ir['FuelLevel']
    Fuel.level_full = drv_info("DriverCarFuelMaxLtr", 0)
    Fuel.pct = ir['FuelLevelPct']
    Fuel.max_pct = drv_info("DriverCarMaxFuelPct", 0)


# Fuel calculations
def fuel_calc():
    if Telem.laps_remaining > 0:
        Fuel.used_lap_req = Fuel.level / Telem.laps_remaining
    else:
        Fuel.used_lap_req = 0.000
    Fuel.used_lap = Fuel.last_level - Fuel.level
    if Fuel.used_lap < 0:
        Fuel.used_lap = Fuel.last_pit_level - Fuel.level
    if Fuel.used_lap > 0:
        Fuel.laps_left = Fuel.level / Fuel.used_lap
        Fuel.eco = Telem.lap_distance / Fuel.used_lap
    else:
        Fuel.laps_left = 999.00
        Fuel.eco = 99.00
    Fuel.eco_req = (Telem.lap_distance * Telem.laps_remaining) / Fuel.level
    if ir['CarIdxPaceLine'][Telem.driver_idx] == -1 and ir['CarIdxTrackSurface'][Telem.driver_idx] == 3 and ir['SessionState'] == 4 and Telem.stint_laps > 1:
        if len(Fuel.used_lap_list) >= 5:
            Fuel.used_lap_list.pop(0)
        Fuel.used_lap_list.append(Fuel.used_lap)
        if len(Fuel.used_lap_list) > 0:
            total = 0
            for used in Fuel.used_lap_list:
                total = total + used
            Fuel.used_lap_avg = total / len(Fuel.used_lap_list)
        if Fuel.used_lap > Fuel.used_lap_max:
            Fuel.used_lap_max = Fuel.used_lap
    if gui.Vars.input["fixed_usage"] > 0:
        if not State.metric:
            Fuel.used_lap_fixed = gui.Vars.input["fixed_usage"] * 3.78541
        else:
            Fuel.used_lap_fixed = gui.Vars.input["fixed_usage"]
    Fuel.level_req = ((Telem.laps_remaining * Fuel.used_lap) - Fuel.level)
    if Fuel.level_req < 0:
        Fuel.level_req = 0.0
    Fuel.level_req_avg = ((Telem.laps_remaining * Fuel.used_lap_avg) - Fuel.level)
    if Fuel.level_req_avg < 0:
        Fuel.level_req_avg = 0.0
    Fuel.level_req_max = ((Telem.laps_remaining * Fuel.used_lap_max) - Fuel.level)
    if Fuel.level_req_max < 0:
        Fuel.level_req_max = 0.0
    Fuel.level_req_fixed = ((Telem.laps_remaining * Fuel.used_lap_fixed) - Fuel.level)
    if Fuel.level_req_fixed < 0:
        Fuel.level_req_fixed = 0.0

    Fuel.stops = round(Fuel.level_req / (Fuel.level_full * Fuel.max_pct), 1)
    if Fuel.stops < 0:
        Fuel.stops = 0
    Fuel.stops_avg = round(Fuel.level_req_avg / (Fuel.level_full * Fuel.max_pct), 1)
    if Fuel.stops_avg < 0:
        Fuel.stops_avg = 0
    Fuel.stops_max = round(Fuel.level_req_max / (Fuel.level_full * Fuel.max_pct), 1)
    if Fuel.stops_max < 0:
        Fuel.stops_max = 0
    Fuel.stops_fixed = round(Fuel.level_req_fixed / (Fuel.level_full * Fuel.max_pct), 1)
    if Fuel.stops_fixed < 0:
        Fuel.stops_fixed = 0


def fueling_thread():
    time.sleep(5)
    status_prev = "pitting"
    while State.ir_connected:
        if gui.Vars.checkboxes["auto_fuel"] and "Qualify" not in session_info("SessionType") and not State.spectator and not State.spotter:
            if "black" not in Telem.flag_list:
                flag_chk = True
            else:
                flag_chk = False
            if ir['CarIdxTrackSurface'][Telem.driver_idx] == 1:
                status = "pitting"
            else:
                status = "driving"
            if status_prev != status:
                if status == "pitting" and flag_chk and ir['OilTemp'] != 77.0:
                    if gui.Vars.combo["auto_fuel_type"] == "Average":
                        if (Telem.laps_remaining + gui.Vars.spin["extra_laps"]) * Fuel.used_lap_avg < ir['FuelLevel']:
                            fuel_add = 0.0
                        else:
                            fuel_add = Fuel.level_req_avg + (Fuel.used_lap_avg * gui.Vars.spin["extra_laps"])
                    elif gui.Vars.combo["auto_fuel_type"] == "Max":
                        if (Telem.laps_remaining + gui.Vars.spin["extra_laps"]) * Fuel.used_lap_max < ir['FuelLevel']:
                            fuel_add = 0.0
                        else:
                            fuel_add = Fuel.level_req_max + (Fuel.used_lap_max * gui.Vars.spin["extra_laps"])
                    else:
                        if (Telem.laps_remaining + gui.Vars.spin["extra_laps"]) * Fuel.used_lap_fixed < ir['FuelLevel']:
                            fuel_add = 0.0
                        else:
                            fuel_add = Fuel.level_req_fixed + (Fuel.used_lap_fixed * gui.Vars.spin["extra_laps"])
                    if len(Fuel.used_lap_list) < 1 or fuel_add > Fuel.level_full:
                        fuel_add = Fuel.level_full
                    if fuel_add + Fuel.last_level <= ir['FuelLevel']:
                        ir.pit_command(11)
                    elif fuel_add + Fuel.last_level > ir['FuelLevel']:
                        ir.pit_command(2, int(round(fuel_add, 0)))
                        while ir['CarIdxTrackSurface'][Telem.driver_idx] == 1:
                            if fuel_add + Fuel.last_level <= ir['FuelLevel']:
                                ir.pit_command(11)
                                break
                            elif ir['FuelLevel'] >= Fuel.level_full:
                                break
                            time.sleep(1 / 60)
            status_prev = status
        time.sleep(1 / 20)


def pit_report():
    if Fuel.stint_used > 0:
        Fuel.stint_used_avg = Fuel.stint_used / Telem.stint_laps
        Fuel.stint_eco = (Telem.stint_laps * Telem.lap_distance) / Fuel.stint_used
    else:
        Fuel.stint_used_avg = 0
        Fuel.stint_eco = 0
    avg_time = "N/A"
    if len(Telem.lap_time_list) > 0:
        avg = 0
        for lap in Telem.lap_time_list:
            avg = avg + lap
        avg_time = duration(avg / len(Telem.lap_time_list))
    ir.unfreeze_var_buffer_latest()
    separator()
    log("Lap " + str(ir['LapCompleted'] + 1) + " Pit Report")
    log(State.sep_2)
    log("Stint: " + str(Telem.stint_laps) + " laps" + ", " + "Avg Time: " + avg_time + ", " + "Avg Used: " + volume(Fuel.stint_used_avg, "short") + ", " + "Avg Eco: " + economy(Fuel.stint_eco) + ", " + "Total Used: " + volume(Fuel.stint_used, "short"))
    log(State.sep_1)
    log("Tire Wear")
    log(State.sep_2)
    log("LF: " + percent(ir['LFwearL']) + " " + percent(ir['LFwearM']) + " " + percent(ir['LFwearR']) + "     " + "RF: " + percent(ir['RFwearL']) + " " + percent(ir['RFwearM']) + " " + percent(ir['RFwearR']))
    log("")
    log("LR: " + percent(ir['LRwearL']) + " " + percent(ir['LRwearM']) + " " + percent(ir['LRwearR']) + "     " + "RR: " + percent(ir['RRwearL']) + " " + percent(ir['RRwearM']) + " " + percent(ir['RRwearR']))
    log(State.sep_1)
    log("Tire Temp")
    log(State.sep_2)
    log("LF: " + temperature(ir['LFtempCL'], "string") + " " + temperature(ir['LFtempCM'], "string") + " " + temperature(ir['LFtempCR'], "string") + "     " +
        "RF: " + temperature(ir['RFtempCL'], "string") + " " + temperature(ir['RFtempCM'], "string") + " " + temperature(ir['RFtempCR'], "string"))
    log("")
    log("LR: " + temperature(ir['LRtempCL'], "string") + " " + temperature(ir['LRtempCM'], "string") + " " + temperature(ir['LRtempCR'], "string") + "     " +
        "RR: " + temperature(ir['RRtempCL'], "string") + " " + temperature(ir['RRtempCM'], "string") + " " + temperature(ir['RRtempCR'], "string"))
    log(State.sep_1)
    State.log_sep = True
    Telem.stint_laps = 0
    Fuel.stint_used = 0.0
    Telem.lap_time_list = []


# The SDK doesn't always work for idx so this is needed, plus spotter and spectator detection
def idx_check():
    uid = drv_info("DriverUserID", 0)
    for idx in range(64, -2, -1):
        try:
            cid = ir['DriverInfo']['Drivers'][idx]['UserID']
            if cid == uid:
                Telem.driver_idx = idx
                if drv_info("Drivers", "IsSpectator") == 1:
                    State.spectator = True
                break
            elif idx == -1:
                Telem.driver_idx = drv_info("DriverCarIdx", 0)
                State.spotter = True
        except IndexError:
            pass


# Shorten DriverInfo calls
def drv_info(group, subgroup):
    if subgroup == 0:
        return ir['DriverInfo'][group]
    else:
        return ir['DriverInfo'][group][Telem.driver_idx][subgroup]
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
    if State.ir_connected:
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
    if not State.log_sep:
        log(State.sep_1)


# Log session info
def session():
    separator()
    log(session_info("SessionType"))
    log(State.sep_2)
    log("Skies: " + sky() + ", " + "Air: " + temperature(ir['AirTemp'], "string") + ", " + "Surface: " + temperature(ir['TrackTempCrew'], "string") + ", " + "Wind: " + wind() + " @ " + speed(ir['WindVel']) + ", " +
        "Humidity: " + percent(ir['RelativeHumidity']) + ", " + "Pressure: " + pressure(ir['AirPressure']) + ", " + "Density: " + density(ir['AirDensity']))
    log(State.sep_1)
    Telem.last_atemp = ir['AirTemp']
    Telem.last_ttemp = ir['TrackTempCrew']
    Telem.laps_completed = 0
    Telem.laps_remaining = 0
    Fuel.used_lap_avg = 0.0
    Fuel.used_lap_max = 0.0
    Fuel.used_lap_list = []
    State.reset_laps = 0
    Fuel.max_pct = drv_info("DriverCarMaxFuelPct", 0)
    State.log_sep = True
    Telem.session = session_info("SessionType")


def air_temp():
    if gui.Vars.checkboxes["temp_updates"]:
        if ir['AirTemp'] > Telem.last_atemp:
            speech = threading.Thread(target=speech_thread, args=("air temp has increased to " + str(round(temperature(ir['AirTemp'], "number"))) + " degrees",))
            speech.start()
        else:
            speech = threading.Thread(target=speech_thread, args=("air temp has decreased to " + str(round(temperature(ir['AirTemp'], "number"))) + " degrees",))
            speech.start()
    separator()
    log("Ambient: " + temperature(ir['AirTemp'], "string"))
    log(State.sep_1)
    State.log_sep = True
    Telem.last_atemp = ir['AirTemp']


def track_temp():
    if gui.Vars.checkboxes["temp_updates"]:
        if ir['TrackTempCrew'] > Telem.last_ttemp:
            speech = threading.Thread(target=speech_thread, args=("track temp has increased to " + str(round(temperature(ir['TrackTempCrew'], "number"))) + " degrees",))
            speech.start()
        else:
            speech = threading.Thread(target=speech_thread, args=("track temp has decreased to " + str(round(temperature(ir['TrackTempCrew'], "number"))) + " degrees",))
            speech.start()
    separator()
    log("Surface: " + temperature(ir['TrackTempCrew'], "string"))
    log(State.sep_1)
    State.log_sep = True
    Telem.last_ttemp = ir['TrackTempCrew']


# iRacing status
def check_iracing():
    try:
        if State.ir_connected and not (ir.is_initialized and ir.is_connected):
            State.ir_connected = False
            ir.shutdown()
            separator()
            log('iRacing Disconnected')
            log(State.sep_1)
            State.log_sep = True
            Telem.session = 0
            State.spectator = False
            State.spotter = False
            Telem.oil_temp_warning = 999.0
            Telem.water_temp_warning = 999.0
        elif not State.ir_connected and ir.startup() and ir.is_initialized and ir.is_connected:
            State.ir_connected = True

            threading.Thread(target=fueling_thread, daemon=True).start()
            threading.Thread(target=warnings_thread, daemon=True).start()

            separator()
            log('iRacing Connected')
            log(State.sep_1)
            State.log_sep = True
            speech = threading.Thread(target=speech_thread, args=("Fuel companion connected",))
            speech.start()
            time.sleep(3)

            # Various one-time calls
            detect_units()
            idx_check()
            track_length = ir['WeekendInfo']['TrackLength']
            track_length_spl = track_length.split()
            Telem.lap_distance = float(track_length_spl[0])
            Fuel.used_lap_list = []
            Fuel.last_level = ir['FuelLevel']
            State.count = ir['LapCompleted'] + 1

            fuel_calc_init()

            # Logging session info
            separator()
            log("Weekend")
            log(State.sep_2)
            log("Track: " + weekend_info("TrackName", 0) + ", " + "Car: " + drv_info("Drivers", "CarPath") + ", " + "Length: " + distance(Telem.lap_distance, "km") + ", " +
                "Date: " + weekend_options("Date", 0) + " " + weekend_options("TimeOfDay", 0) + weekend_options("TimeOfDay", 1) + ", " + "Rubber: " + session_info("SessionTrackRubberState") + ", " + "Max Fuel: " + percent(Fuel.max_pct))
            State.log_sep = False
            session()

            # Needed to "reset" keyboard module for some reason
            time.sleep(1)
            keyboard.write("")
    except ConnectionResetError:
        pass


# Main loop (run in thread because of GUI weirdness)
def main():
    # Freeze telemetry for consistent data
    ir.freeze_var_buffer_latest()

    # Session type retrieval and change detection
    if State.ir_connected:
        session_type = session_info("SessionType")
    else:
        session_type = Telem.session
    if session_type != Telem.session:
        session()

    # Update binary lists
    Telem.flag = ir['SessionFlags']
    Telem.engine = ir['EngineWarnings']

    # Engine temperature warnings
    if gui.Vars.checkboxes["engine_warnings"]:
        # Oil
        if "oil_temp_warning" in Telem.engine_list:
            if not Telem.oil_warning_prev and Telem.oil_temp_warning == 999.0:
                Telem.oil_temp_warning = ir['OilTemp']
            Telem.oil_warning_prev = True
        else:
            Telem.oil_warning_prev = False
        if not State.metric:
            oil_threshold = (gui.Vars.input["oil_threshold"] - 32) * (5 / 9)
        else:
            oil_threshold = gui.Vars.input["oil_threshold"]
        if Telem.oil_temp_warning >= oil_threshold:
            if ir['OilTemp'] >= Telem.oil_temp_warning:
                Telem.oil_trigger = True
            if ir['OilTemp'] <= (Telem.oil_temp_warning - 3):
                if Telem.oil_warned:
                    threading.Thread(target=speech_thread, args=("oil temp has fallen to " + str(round(temperature(ir['OilTemp'], "number"))) + " degrees",)).start()
                    Telem.oil_warned = False
        elif Telem.oil_temp_warning < oil_threshold:
            if ir['OilTemp'] >= oil_threshold:
                Telem.oil_trigger = True
            if ir['OilTemp'] <= (oil_threshold - 3):
                if Telem.oil_warned:
                    threading.Thread(target=speech_thread, args=("oil temp has fallen to " + str(round(temperature(ir['OilTemp'], "number"))) + " degrees",)).start()
                    Telem.oil_warned = False
        if Telem.oil_trigger and not Telem.oil_warned:
            threading.Thread(target=speech_thread, args=("oil temp has risen to " + str(round(temperature(ir['OilTemp'], "number"))) + " degrees",)).start()
            Telem.oil_warned = True
        Telem.oil_trigger = False

        # Water
        if "water_temp_warning" in Telem.engine_list:
            if not Telem.water_warning_prev and Telem.water_temp_warning == 999.0:
                Telem.water_temp_warning = ir['WaterTemp']
            Telem.water_warning_prev = True
        else:
            Telem.water_warning_prev = False
        if not State.metric:
            water_threshold = (gui.Vars.input["water_threshold"] - 32) * (5 / 9)
        else:
            water_threshold = gui.Vars.input["water_threshold"]
        if Telem.water_temp_warning >= water_threshold:
            if ir['WaterTemp'] >= Telem.water_temp_warning:
                Telem.water_trigger = True
            if ir['WaterTemp'] <= (Telem.water_temp_warning - 3):
                if Telem.water_warned:
                    threading.Thread(target=speech_thread, args=("water temp has fallen to " + str(round(temperature(ir['WaterTemp'], "number"))) + " degrees",)).start()
                    Telem.water_warned = False
        elif Telem.water_temp_warning < water_threshold:
            if ir['WaterTemp'] >= water_threshold:
                Telem.water_trigger = True
            if ir['WaterTemp'] <= (water_threshold - 3):
                if Telem.water_warned:
                    threading.Thread(target=speech_thread, args=("water temp has fallen to " + str(round(temperature(ir['WaterTemp'], "number"))) + " degrees",)).start()
                    Telem.water_warned = False
        if Telem.water_trigger and not Telem.water_warned:
            threading.Thread(target=speech_thread, args=("water temp has risen to " + str(round(temperature(ir['WaterTemp'], "number"))) + " degrees",)).start()
            Telem.water_warned = True
        Telem.water_trigger = False

    # Check air and track temperatures
    if ((ir['AirTemp'] * 1.8) + 32) > ((Telem.last_atemp * 1.8) + 32) + 1 or ((ir['AirTemp'] * 1.8) + 32) < ((Telem.last_atemp * 1.8) + 32) - 1:
        air_temp()
    if ((ir['TrackTempCrew'] * 1.8) + 32) > ((Telem.last_ttemp * 1.8) + 32) + 3 or ((ir['TrackTempCrew'] * 1.8) + 32) < ((Telem.last_ttemp * 1.8) + 32) - 3:
        track_temp()

    # Practice race fuel percent and resetting
    if session_info("SessionType") == "Offline Testing" or session_info("SessionType") == "Practice":
        if drv_info("DriverCarMaxFuelPct", 0) == 1:
            Fuel.max_pct = gui.Vars.spin["practice_fuel_percent"] / 100

        if ir['OilTemp'] == 77.0 and State.reset_laps == 1:
            Telem.laps_completed = 0
            Fuel.used_lap_avg = 0.0
            Fuel.used_lap_max = 0.0
            Fuel.used_lap_list = []
            State.reset_laps = 0
        elif ir['OilTemp'] != 77.0:
            State.reset_laps = 1

    # Lap completion trigger
    if ir['LapCompleted'] < State.count:
        State.count = ir['LapCompleted'] + 1
    if ir['LapCompleted'] > State.count + 1:
        State.count = ir['LapCompleted'] + 1
    elif ir['LapCompleted'] == State.count:
        Fuel.level = ir['FuelLevel']
        Fuel.pct = ir['FuelLevelPct']
        State.count = State.count + 1
        State.trigger = True

    # Things to do on lap complete
    if State.trigger and Fuel.level > 0:
        if session_info("SessionType") == "Offline Testing" or session_info("SessionType") == "Practice":
            Telem.laps_completed = Telem.laps_completed + 1
        else:
            Telem.laps_completed = ir['LapCompleted']
        if Telem.laps_completed <= 0:
            Telem.stint_laps = 0
        else:
            Telem.stint_laps = Telem.stint_laps + 1

        # Estimate laps based on time remaining if session laps aren't set
        if ir['SessionLapsRemain'] > 5000 and ir['LapLastLapTime'] > 1:
            Telem.laps_remaining = math.ceil(ir['SessionTimeRemain'] / ir['LapLastLapTime'])
        elif ir['SessionLapsRemain'] > 5000 and ir['LapLastLapTime'] < 1:
            Telem.laps_remaining = math.ceil(ir['SessionTimeRemain'] / (Telem.lap_distance / (100 / 3600)))
        elif ir['SessionLapsRemain'] <= 0:
            Telem.laps_remaining = 1
        else:
            Telem.laps_remaining = ir['SessionLapsRemain'] + 1

        # Use mock race laps for practices
        if session_info("SessionType") == "Offline Testing" or session_info("SessionType") == "Practice":
            Telem.laps_remaining = gui.Vars.spin["practice_laps"] - Telem.laps_completed

        fuel_calc()

        # Things to do if not under caution or in pit
        if ir['CarIdxPaceLine'][Telem.driver_idx] == -1 and ir['CarIdxTrackSurface'][Telem.driver_idx] == 3 and ir['SessionState'] == 4 and Telem.stint_laps > 1:
            # TTS callouts
            if gui.Vars.checkboxes["tts_fuel"] and session_type != "Lone Qualify":
                threading.Thread(target=speech_thread, args=(str(round(Fuel.laps_left, 2)) + " laps, " + volume(Fuel.used_lap, "long"),)).start()
            # Text callouts
            if gui.Vars.checkboxes["txt_fuel"] and session_type != "Lone Qualify":
                time.sleep(0.50)
                ir.chat_command(1)
                time.sleep(0.1)
                keyboard.write("## Previous lap - " + str(round(Fuel.laps_left, 2)) + " laps, " + volume(Fuel.used_lap, "short") + ", " + economy(Fuel.eco) + ", " + volume(Fuel.level_req, "short") + "(" + str(Fuel.stops) + ") extra ##")
                time.sleep(0.1)
                keyboard.send('enter')
                time.sleep(0.1)
                ir.chat_command(3)

        # Info to log
        ir.unfreeze_var_buffer_latest()
        time.sleep(1)
        if len(Telem.lap_time_list) > 0:
            lap_list_max = max(Telem.lap_time_list)
        else:
            lap_list_max = 999
        if 0 < ir['LapLastLapTime'] < (lap_list_max + 5):
            Telem.lap_time_list.append(ir['LapLastLapTime'])

        lap_time = duration(ir['LapLastLapTime'])
        if ir['LapLastLapTime'] <= 0.0:
            lap_time = "N/A"

        if Telem.laps_completed <= ir['SessionLapsTotal']:
            if session_info("SessionType") == "Offline Testing" or session_info("SessionType") == "Practice":
                log("Lap " + str(ir['LapCompleted']) + " [Time: " + lap_time + " | Laps: " + str(round(Fuel.laps_left, 2)) + " | Used: " + volume(Fuel.used_lap, "short") + " | Eco: " + economy(Fuel.eco) + "]")
            else:
                log("Lap " + str(ir['LapCompleted']) + " [Time: " + lap_time + " | Laps: " + str(round(Fuel.laps_left, 2)) + " | Used: " + volume(Fuel.used_lap, "short") + " | Usage Req: " + volume(Fuel.used_lap_req, "short") + " | Eco: " +
                    economy(Fuel.eco) + " | Eco Req: " + economy(Fuel.eco_req) + " | Level Req: " + volume(Fuel.level_req, "short") + "]")
            State.log_sep = False

        # Lap finishing actions
        Fuel.last_level = Fuel.level
        State.trigger = False
    elif State.trigger and Fuel.level <= 0:
        Fuel.last_level = Fuel.level
        State.trigger = False

    # Pit report
    if ir['CarIdxTrackSurface'][Telem.driver_idx] != State.surface and ir['CarIdxTrackSurface'][
        Telem.driver_idx] == 1 or ir['CarIdxTrackSurface'][Telem.driver_idx] != State.surface and \
            ir['CarIdxTrackSurface'][Telem.driver_idx] == -1:
        Fuel.stint_used = Fuel.last_pit_level - ir['FuelLevel']
        if Fuel.stint_used <= 0:
            Fuel.stint_used = Fuel.last_pit_level - Fuel.last_level
        time.sleep(3)
        if Telem.stint_laps > 0:
            pit_report()

    if State.surface == 1 and ir['CarIdxTrackSurface'][Telem.driver_idx] != 1:
        Fuel.last_pit_level = ir['FuelLevel']
    if State.surface == -1 and ir['CarIdxTrackSurface'][Telem.driver_idx] != -1:
        Fuel.last_pit_level = ir['FuelLevel']

    State.surface = ir['CarIdxTrackSurface'][Telem.driver_idx]


def init():
    time.sleep(1)
    log("iR Fuel Companion " + State.version)
    log(State.sep_1)

    # Check for updates
    if gui.Vars.checkboxes["check_updates"]:
        try:
            with urllib.request.urlopen('https://www.renovamenia.com/files/iracing/other/iR_Fuel_Companion/version.txt') as file:
                server_version = file.read().decode('utf-8').strip("v").split('.')
                local_version = State.version.strip("v").split('.')
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
                    log(State.sep_1)
        except urllib.error.URLError as error:
            log("Update checking failed, cannot connect to update server! " + str(error))
            log(State.sep_1)
    try:
        # Check connection and start (or not) loop
        while True:
            check_iracing()
            if State.ir_connected:
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

    gui.main(State.version)
