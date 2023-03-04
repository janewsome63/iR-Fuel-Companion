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


# Variables and lists
# Global
class State:
    connected = False


# Static dictionaries
lang = {
    "no_connection": "no eye racing connection",
    "separator_a": "=" * 138,
    "separator_b": "-" * 138,
    "version": "v1.0.0",
}

# Mallable dictionaries
status = {}
trigger = {}
eco = {}
level = {}
stops = {}
window = {}
usage = {}
stint = {}
lap = {}
weather = {}
car = {}
session = {}
misc = {}


# Set dictionary values on connect
def init_vars():
    State.connected = True

    # Car telem
    car['engine_hex'] = ir['EngineWarnings']
    car['engine_list'] = []
    car['location'] = ir['PlayerTrackSurface']
    car['name'] = drv_info("Drivers", "CarPath")
    car['oil_warn_value'] = 999.0
    car['temp_oil'] = ir['OilTemp']
    car['temp_oil_prev'] = 0.0
    car['temp_water'] = ir['WaterTemp']
    car['temp_water_prev'] = 0.0
    car['water_warn_value'] = 999.0

    # Fuel economy
    eco['avg'] = 0.0
    eco['high'] = 0.0
    eco['low'] = 0.0
    eco['max'] = 0.0
    eco['prev'] = 0.0
    eco['req'] = 0.0

    # Lap
    lap['completed'] = ir['LapCompleted']
    lap['dist'] = ir['LapDist']
    lap['dist_prev'] = 0.0
    lap['next'] = ir['LapCompleted'] + 1
    lap['pit'] = 0
    lap['remaining'] = ir['SessionLapsRemain'] + 1
    lap['time_avg'] = 0.0
    lap['time_prev'] = ir['LapLastLapTime']
    lap['times'] = []
    lap['total'] = ir['SessionLapsTotal']

    # Fuel levels
    level['current'] = ir['FuelLevel']
    level['current_pct'] = ir['FuelLevelPct']
    level['current_prev'] = 0.0
    level['full'] = drv_info("DriverCarFuelMaxLtr", 0)
    level['full_pct'] = drv_info("DriverCarMaxFuelPct", 0)
    level['pit'] = 0.0
    level['prev'] = 0.0
    level['req_avg'] = 0.0
    level['req_high'] = 0.0
    level['req_low'] = 0.0
    level['req_max'] = 0.0
    level['req_prev'] = 0.0

    # Misc
    misc['date'] = weekend_options("Date", 0)
    misc['idx'] = 0
    misc['incidents'] = ir['PlayerCarMyIncidentCount']
    misc['incidents_prev'] = ir['PlayerCarMyIncidentCount']
    misc['rubber'] = session_info("SessionTrackRubberState")
    misc['timer_start'] = time.perf_counter()
    misc['time'] = weekend_options("TimeOfDay", 0) + weekend_options("TimeOfDay", 1)
    track_length = ir['WeekendInfo']['TrackLength']
    track_length_spl = track_length.split()
    misc['track_length'] = float(track_length_spl[0])
    misc['track_name'] = weekend_info("TrackName", 0)

    # Session
    session['flag_hex'] = ir['SessionFlags']
    session['flag_list'] = []
    session['name'] = session_info("SessionType")
    session['state'] = ir['SessionState']
    session['time'] = ir['SessionTime']
    session['time_remaining'] = ir['SessionTimeRemain']
    session['time_total'] = ir['SessionTimeTotal']

    # Statuses
    status['active_reset'] = False
    status['driving'] = False
    status['imperial'] = False
    status['incident'] = False
    status['oil_temp_warning'] = False
    status['pitting'] = False
    status['practice'] = False
    status['separator'] = True
    # status['spectator'] = False
    # status['spotter'] = False
    status['timed'] = False
    status['towing'] = False
    status['water_temp_warning'] = False

    # Stint
    stint['avg'] = 0.0
    stint['completed'] = 0
    stint['eco'] = 0.0
    stint['remaining_avg'] = 0.0
    stint['remaining_high'] = 0.0
    stint['remaining_low'] = 0.0
    stint['remaining_max'] = 0.0
    stint['remaining_prev'] = 0.0
    stint['time_avg'] = 0.0
    stint['times'] = []
    stint['used'] = 0.0

    # Stops required
    stops['avg'] = 0
    stops['high'] = 0
    stops['low'] = 0
    stops['max'] = 0
    stops['prev'] = 0

    # Triggers
    trigger['active_reset'] = False
    trigger['air'] = "None"
    trigger['driving'] = False
    trigger['init'] = True
    trigger['lap'] = False
    trigger['oil'] = False
    trigger['pitting'] = False
    trigger['car_reset'] = False
    trigger['session'] = "None"
    trigger['towing'] = False
    trigger['track'] = "None"
    trigger['water'] = False

    # Fuel usage
    usage['avg'] = 0.0
    usage['high'] = 0.0
    usage['low'] = 0.0
    usage['list'] = []
    usage['max'] = 0.0
    usage['prev'] = 0.0
    usage['req'] = 0.0

    # Weather
    weather['density'] = ir['AirDensity']
    weather['humidity'] = ir['RelativeHumidity']
    weather['pressure'] = ir['AirPressure']
    weather['sky'] = "N/A"
    weather['temp_air'] = ir['AirTemp']
    weather['temp_air_prev'] = ir['AirTemp']
    weather['temp_track'] = ir['TrackTempCrew']
    weather['temp_track_prev'] = ir['TrackTempCrew']
    weather['wind_dir'] = "N/A"
    weather['wind_vel'] = ir['WindVel']

    # Fuel window
    window['avg'] = 0
    window['high'] = 0
    window['low'] = 0
    window['max'] = 0
    window['prev'] = 0


# Variable actions to run on disconnect
def deinit_vars():
    State.connected = False
    status['spotter'] = False


# Specific variable actions
def reset_vars(name):
    if "car" in name:
        if gui.Vars.input['practice_laps'] != 0:
            lap['times'] = []
            usage['list'] = []
        misc['timer_start'] = time.perf_counter()
        trigger['oil'] = False
        trigger['water'] = False
    if "lap" in name:
        lap['dist'] = ir['LapDist']
        lap['dist_prev'] = ir['LapDist']
        status['active_reset'] = False
    if "session" in name:
        lap['completed'] = 0
        lap['next'] = ir['LapCompleted'] + 1
        lap['pit'] = 0
        lap['remaining'] = ir['SessionLapsRemain'] + 1
        lap['times'] = []
        lap['total'] = ir['SessionLapsTotal']
        misc['date'] = weekend_options("Date", 0)
        misc['rubber'] = session_info("SessionTrackRubberState")
        misc['time'] = weekend_options("TimeOfDay", 0) + weekend_options("TimeOfDay", 1)
        session['name'] = session_info("SessionType")
        usage['list'] = []
        weather['temp_air_prev'] = ir['AirTemp']
        weather['temp_track_prev'] = ir['TrackTempCrew']
    if "stint" in name:
        if trigger['car_reset'] and gui.Vars.input['practice_laps'] != 0:
            lap['completed'] = 0
        stint['completed'] = 0
        stint['times'] = []


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

# Units functions
# Return converted temperature
def temperature(value, style):
    if status['imperial']:
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
    if status['imperial']:
        return str(round(value * 2.2369362920544025, 1)) + "mph"
    else:
        return str(round(value * 3.6, 1)) + "kph"


# Return converted pressure
def pressure(value):
    if status['imperial']:
        return str(round(value, 1)) + "hg"
    else:
        return str(round(value * 3.38639, 1)) + "kpa"


# Return converted density
def density(value):
    if status['imperial']:
        return str(round(value * 0.062427960576145, 2)) + "lb/ft^3"
    else:
        return str(round(value, 2)) + "kg/m^3"


# Return converted distance
def distance(value, magnitude):
    if status['imperial']:
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
    if status['imperial']:
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
    if status['imperial']:
        return str(round(value * 2.352145833, 2)) + "mpg"
    else:
        return str(round(value, 2)) + "km/l"


# Return formatted percentage
def percent(value):
    return str(round(value * 100, 2)) + "%"


# Return formatted time
def duration(value):
    return str(round(value, 3)) + "s"


# Controls functions
# Save binding
def bind_set(bind, event):
    if keybind.Vars.button == "esc":
        gui.event(event, "")
    elif keybind.Vars.button != "None":
        getattr(gui.Binds, "keys")[bind] = keybind.Vars.button
        controls_name(bind)
        gui.event(event, "")


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
                elif gui.Binds.recording["auto_fuel_info"]:
                    bind_set('auto_fuel_info', 'bind-auto_fuel_info')
                time.sleep(1 / 20)


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
            if State.connected:
                for type in gui.Vars.combo["auto_fuel_type"]:
                    if (lap['left'] + gui.Vars.spin["extra_laps"]) * usage[type] < level['current']:
                        add = 0.0
                    else:
                        add = level['req_' + type] + (usage[type] * gui.Vars.spin["extra_laps"])
                    if add + level['prev'] <= level['current']:
                        ir.pit_command(11)
                    if add + level['prev'] > level['current']:
                        ir.pit_command(2, int(round(add, 0)))
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
            if State.connected:
                threading.Thread(target=speech_thread, args=("air temp is " + str(round(temperature(ir['AirTemp'], "number"))) + " and track temp is " + str(round(temperature(ir['TrackTempCrew'], "number"))),)).start()
            else:
                threading.Thread(target=speech_thread, args=(lang['no_connection'],)).start()
            time.sleep(0.75)

        # Print previous lap usage info
        if gui.Binds.keys["previous_usage"] == keybind.Vars.button:
            time.sleep(0.25)
            if State.connected:
                txt_prev_lap()
            else:
                threading.Thread(target=speech_thread, args=(lang['no_connection'],)).start()
            time.sleep(0.75)

        # Print required usage info
        if gui.Binds.keys["required_usage"] == keybind.Vars.button:
            time.sleep(0.25)
            if State.connected:
                if gui.Vars.input['practice_laps'] == 0 and status['practice']:
                    ir.chat_command(1)
                    time.sleep(0.05)
                    keyboard.write("## Required Info - " + str(lap['remaining']) + " laps est ##")
                    time.sleep(0.05)
                    keyboard.send('enter')
                    time.sleep(0.05)

                    if gui.Vars.input['usage_high'] > 0.0:
                        ir.chat_command(1)
                        time.sleep(0.05)
                        keyboard.write("## High - " + str(round(stint['remaining_high'], 1)) + " laps, " + volume(usage['high'], "short") + ", " + economy(eco['high']) + " ##")
                        time.sleep(0.05)
                        keyboard.send('enter')
                        time.sleep(0.05)

                    if gui.Vars.input['usage_low'] > 0.0:
                        ir.chat_command(1)
                        time.sleep(0.05)
                        keyboard.write("## Low - " + str(round(stint['remaining_low'], 1)) + " laps, " + volume(usage['low'], "short") + ", " + economy(eco['low']) + " ##")
                        time.sleep(0.05)
                        keyboard.send('enter')
                        time.sleep(0.05)
                else:
                    ir.chat_command(1)
                    time.sleep(0.05)
                    keyboard.write("## Required Info - " + str(lap['remaining']) + " laps, " + volume(usage['req'], "short") + ", " + economy(eco['req']) + " ##")
                    time.sleep(0.05)
                    keyboard.send('enter')
                    time.sleep(0.05)

                    if gui.Vars.input['usage_high'] > 0.0:
                        ir.chat_command(1)
                        time.sleep(0.05)
                        keyboard.write("## High - " + str(round(stint['remaining_high'], 1)) + " laps, " + volume(usage['high'], "short") + ", " + economy(eco['high']) + ", " + volume(level['req_high'], "short") + " (" + str(stops['high']) + ", " + str(window['high']) + ") ##")
                        time.sleep(0.05)
                        keyboard.send('enter')
                        time.sleep(0.05)

                    if gui.Vars.input['usage_low'] > 0.0:
                        ir.chat_command(1)
                        time.sleep(0.05)
                        keyboard.write("## Low - " + str(round(stint['remaining_low'], 1)) + " laps, " + volume(usage['low'], "short") + ", " + economy(eco['low']) + ", " + volume(level['req_low'], "short") + " (" + str(stops['low']) + ", " + str(window['low']) + ") ##")
                        time.sleep(0.05)
                        keyboard.send('enter')
                        time.sleep(0.05)
                ir.chat_command(3)
            else:
                threading.Thread(target=speech_thread, args=(lang['no_connection'],)).start()
            time.sleep(0.75)

        # Print auto fuel info
        if gui.Binds.keys['auto_fuel_info'] == keybind.Vars.button:
            time.sleep(0.25)
            if State.connected:
                if gui.Vars.input['practice_laps'] == 0 and status['practice']:
                    ir.chat_command(1)
                    time.sleep(0.05)
                    keyboard.write("## Auto Fueling Info - No type active ##")
                    time.sleep(0.05)
                    keyboard.send('enter')
                    time.sleep(0.05)

                    ir.chat_command(1)
                    time.sleep(0.05)
                    keyboard.write("## Avg - " + str(round(stint['remaining_avg'], 1)) + " laps, " + volume(usage['avg'], "short") + ", " + economy(eco['avg']) + " ##")
                    time.sleep(0.05)
                    keyboard.send('enter')
                    time.sleep(0.05)

                    ir.chat_command(1)
                    time.sleep(0.05)
                    keyboard.write("## Max - " + str(round(stint['remaining_max'], 1)) + " laps, " + volume(usage['max'], "short") + ", " + economy(eco['max']) + " ##")
                    time.sleep(0.05)
                    keyboard.send('enter')
                    time.sleep(0.05)
                else:
                    current_type = "max"
                    auto_fuel_types = (("Average", "avg"), ("Max", "max"), ("Fixed", "high"))
                    for type in auto_fuel_types:
                        if gui.Vars.combo['auto_fuel_type'] == type[0]:
                            current_type = type[1]

                    if level['req_' + current_type] > level['full']:
                        fuel_add = level['full']
                    else:
                        fuel_add = level['req_' + current_type]

                    ir.chat_command(1)
                    time.sleep(0.05)
                    keyboard.write("## Auto Fueling Info - " + gui.Vars.combo['auto_fuel_type'] + " type active, " + volume(fuel_add, "short") + " will be added ##")
                    time.sleep(0.05)
                    keyboard.send('enter')
                    time.sleep(0.05)

                    ir.chat_command(1)
                    time.sleep(0.05)
                    keyboard.write("## Avg - " + str(round(stint['remaining_avg'], 1)) + " laps, " + volume(usage['avg'], "short") + ", " + economy(eco['avg']) + ", " + volume(level['req_avg'], "short") + " (" + str(stops['avg']) + ", " + str(window['avg']) + ") ##")
                    time.sleep(0.05)
                    keyboard.send('enter')
                    time.sleep(0.05)

                    ir.chat_command(1)
                    time.sleep(0.05)
                    keyboard.write("## Max - " + str(round(stint['remaining_max'], 1)) + " laps, " + volume(usage['max'], "short") + ", " + economy(eco['max']) + ", " + volume(level['req_max'], "short") + " (" + str(stops['max']) + ", " + str(window['max']) + ") ##")
                    time.sleep(0.05)
                    keyboard.send('enter')
                    time.sleep(0.05)
                ir.chat_command(3)
            else:
                threading.Thread(target=speech_thread, args=(lang['no_connection'],)).start()
            time.sleep(0.75)
        time.sleep(1 / 20)


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
        if session['flag_hex'] & flag_hexes[name] == flag_hexes[name]:
            session['flag_list'].append(name)

    # Add current engine warning to list
    def engine_compare(name):
        if car['engine_hex'] & engine_hexes[name] == engine_hexes[name]:
            car['engine_list'].append(name)

    # Run comparisons
    while State.connected:
        session['flag_list'] = []
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

        car['engine_list'] = []
        engine_compare("water_temp_warning")
        engine_compare("fuel_pressure_warning")
        engine_compare("oil_pressure_warning")
        engine_compare("engine_stalled")
        engine_compare("pit_speed_limiter")
        engine_compare("rev_limiter_active")
        engine_compare("oil_temp_warning")
        time.sleep(1)


# Read settings.ini
def read_config():
    config = configparser.ConfigParser()
    config.read(gui.Vars.user_dir + '\\settings.ini')

    # Fueling
    if config.has_option('Fueling', 'auto_fuel'):
        gui.Vars.checkboxes["auto_fuel"] = config.getboolean('Fueling', 'auto_fuel')
    if config.has_option('Fueling', 'auto_fuel_type'):
        gui.Vars.combo["auto_fuel_type"] = config.get('Fueling', 'auto_fuel_type')
    if config.has_option('Fueling', 'usage_high'):
        gui.Vars.input["usage_high"] = config.getfloat('Fueling', 'usage_high')
    if config.has_option('Fueling', 'usage_low'):
        gui.Vars.input["usage_low"] = config.getfloat('Fueling', 'usage_low')
    if config.has_option('Fueling', 'extra_laps'):
        gui.Vars.spin["extra_laps"] = config.getint('Fueling', 'extra_laps')

    # Updates
    if config.has_option('Updates', 'check_updates'):
        gui.Vars.checkboxes["check_updates"] = config.getboolean('Updates', 'check_updates')
    if config.has_option('Updates', 'engine_warnings'):
        gui.Vars.checkboxes["engine_warnings"] = config.getboolean('Updates', 'engine_warnings')
    if config.has_option('Updates', 'oil_threshold'):
        gui.Vars.input["oil_threshold"] = config.getint('Updates', 'oil_threshold')
    if config.has_option('Updates', 'water_threshold'):
        gui.Vars.input["water_threshold"] = config.getint('Updates', 'water_threshold')
    if config.has_option('Updates', 'tts_fuel'):
        gui.Vars.checkboxes["tts_fuel"] = config.getboolean('Updates', 'tts_fuel')
    if config.has_option('Updates', 'txt_fuel'):
        gui.Vars.checkboxes["txt_fuel"] = config.getboolean('Updates', 'txt_fuel')
    if config.has_option('Updates', 'temp_updates'):
        gui.Vars.checkboxes["temp_updates"] = config.getboolean('Updates', 'temp_updates')

    # Practice
    if config.has_option('Practice', 'laps'):
        gui.Vars.input["practice_laps"] = config.getint('Practice', 'laps')
    if config.has_option('Practice', 'fuel_percent'):
        gui.Vars.input["practice_fuel_percent"] = config.getint('Practice', 'fuel_percent')

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
    if config.has_option('Controls', 'auto_fuel_info'):
        gui.Binds.keys["auto_fuel_info"] = config.get('Controls', 'auto_fuel_info')
        controls_name('auto_fuel_info')


# Fuel functions
# Lap complete calculations
def fuel_calc():
    if trigger['lap']:
        # Current fuel usage
        if level['current'] < level['prev']:
            usage['prev'] = level['prev'] - level['current']
        elif level['current'] >= level['prev']:
            usage['prev'] = level['pit'] - level['current']

        # Required fuel usage
        if lap['remaining'] > 0:
            usage['req'] = level['current'] / lap['remaining']
        else:
            usage['req'] = level['current']

        # Required fuel economy
        eco['req'] = (misc['track_length'] * lap['remaining']) / level['current']

        # Only do these actions while not in the pits, under caution, on out lap, or on active reset lap
        if not status['incident'] and not status['caution'] and car['location'] == 3 and session['state'] == 4 and stint['completed'] > 1 and not status['active_reset']:

            # Add current usage to list (and keep previous 5 laps)
            if len(usage['list']) >= 5:
                usage['list'].pop(0)
            usage['list'].append(usage['prev'])

            # Average fuel usage
            if len(usage['list']) > 0:
                total = 0
                for used in usage['list']:
                    total = total + used
                usage['avg'] = total / len(usage['list'])

            # Max fuel usage
            if usage['prev'] > usage['max']:
                usage['max'] = usage['prev']

        # Fixed fuel usage
        fixed_types = ['high', 'low']
        for type in fixed_types:
            if gui.Vars.input['usage_' + type] > 0:
                if status['imperial']:
                    usage[type] = gui.Vars.input['usage_' + type] * 3.78541
                else:
                    usage[type] = gui.Vars.input['usage_' + type]

        # Consolidated calculations
        fuel_types = ['prev', 'avg', 'max', 'high', 'low']
        for type in fuel_types:
            # Laps remaining
            try:
                stint['remaining_' + type] = level['current'] / usage[type]
            except ZeroDivisionError:
                stint['remaining_' + type] = 0

            # Fuel economy
            try:
                eco[type] = misc['track_length'] / usage[type]
            except ZeroDivisionError:
                eco[type] = 0.0

            # Required fuel levels
            level['req_' + type] = ((lap['remaining'] * usage[type]) - level['current'])
            if level['req_' + type] < 0:
                level['req_' + type] = 0.0

            # Number of pit stops needed
            stops[type] = round(level['req_' + type] / (level['full']), 1)
            if stops[type] < 0.0:
                stops[type] = 0.0

            # Pit window opening laps
            try:
                total = lap['total']
                est_stint = math.floor(level['full'] / usage[type])
                while True:
                    if total - est_stint < lap['pit']:
                        if total > lap['completed'] + stint['remaining_' + type]:
                            window[type] = total - est_stint
                        else:
                            window[type] = total
                        if window[type] < 0:
                            window[type] = 0
                        break
                    else:
                        total = total - est_stint
            except ZeroDivisionError:
                window[type] = lap['total']


# Thread to control auto fuel
def fueling_thread():
    while State.connected:
        if gui.Vars.checkboxes['auto_fuel'] and gui.Vars.input['practice_laps'] != 0 or gui.Vars.checkboxes['auto_fuel'] and not status['practice']:
            # Check if driver is pitting, doesn't have a black flag, is not in a qualifying session, and is not a spectator or spotter
            if status['pitting'] and trigger['pitting'] and "black" not in session['flag_list'] and "Qualify" not in session['name'] and not status['spectator'] and not status['spotter']:
                # Convert auto fuel type names to their shortened versions
                type = "max"
                auto_fuel_types = (("Average", "avg"), ("Max", "max"), ("Fixed", "high"))
                for i in auto_fuel_types:
                    if gui.Vars.combo['auto_fuel_type'] == i[0]:
                        type = i[1]
                # If fuel to add is less than current fuel level, add nothing
                if (lap['remaining'] + gui.Vars.spin['extra_laps']) * usage[type] < level['current']:
                    fuel_add = 0.0
                # If there is no fuel data or fuel to add is greater than full, add full
                elif len(usage['list']) < 1 or level['req_' + type] > level['full']:
                    fuel_add = level['full']
                # In normal circumstances, add required level and the user defined extra
                else:
                    fuel_add = level['req_' + type] + (usage[type] * gui.Vars.spin['extra_laps'])
                # Send deselect fuel command if fuel to add is less than current fuel level
                if fuel_add + level['current_prev'] <= level['current']:
                    ir.pit_command(11)
                # Send fuel add command (rounding up)
                elif fuel_add + level['current_prev'] > level['current']:
                    ir.pit_command(2, int(math.ceil(fuel_add)))
                    try:
                        # While recieving service, check levels
                        while status['pitting']:
                            # If enough fuel has been added, send deselect fuel command and end loop
                            if fuel_add + level['current_prev'] <= level['current']:
                                ir.pit_command(11)
                                break
                            # If current fuel level is full, end loop
                            elif round(level['current'], 4) == level['full']:
                                break
                            time.sleep(1 / 60)
                    except AttributeError:
                        pass
        time.sleep(1 / 10)


# Print to log/alert functions
# Engine warning updates
def engine_warnings():
    if gui.Vars.checkboxes["engine_warnings"] and status['driving']:
        # Consolidated temperature warnings
        temp_warning_types = ("oil", "water")
        for type in temp_warning_types:
            # Check if car has been reset and reset stored info
            if trigger['car_reset']:
                car[type + '_warn_value'] = 999.0
                status[type + '_temp_warning'] = False
                trigger[type] = False

            # If the user threshold is greater than 0, use that
            if gui.Vars.input[type + '_threshold'] > 0:
                # Set user defined threshold
                if status['imperial']:
                    car[type + '_warn_value'] = (gui.Vars.input[type + '_threshold'] - 32) * (5 / 9)
                else:
                    car[type + '_warn_value'] = gui.Vars.input[type + '_threshold']
            else:
                # Determine the value at which the built-in warning turns on, and set warning status
                if type + "_temp_warning" in car['engine_list']:
                    if not status[type + '_temp_warning']:
                        car[type + '_warn_value'] = car['temp_' + type]
                        status[type + '_temp_warning'] = True
                else:
                    status[type + '_temp_warning'] = False

            # Check if the user should be warned, or alert that the temperature has fallen below threshold and reset
            if car['temp_' + type] >= car[type + '_warn_value']:
                warn = True
            elif car['temp_' + type] <= (car[type + '_warn_value'] - 5) and trigger[type]:
                threading.Thread(target=speech_thread, args=(type + " temp has fallen to " + str(round(temperature(car['temp_' + type], "number"))) + " degrees",)).start()
                trigger[type] = False
                warn = False
            else:
                warn = False

            # Warn user of temperature above threshold
            if warn and not trigger[type]:
                threading.Thread(target=speech_thread, args=(type + " temp has risen to " + str(round(temperature(car['temp_' + type], "number"))) + " degrees",)).start()
                trigger[type] = True


# Actions to do on lap complete
def lap_alerts():
    # Do end of lap updates/alerts
    if not status['caution'] and car['location'] == 3 and session['state'] == 4 and stint['completed'] > 0 and "Qualify" not in session['name'] and not status['active_reset']:
        # TTS callouts
        if gui.Vars.checkboxes['tts_fuel']:
            threading.Thread(target=speech_thread, args=(str(round(stint['remaining_prev'], 1)) + " laps, " + volume(usage['prev'], "long"),)).start()
        # Text callouts
        if gui.Vars.checkboxes['txt_fuel']:
            txt_prev_lap()

    # Write previous lap info to logs
    if session['state'] < 6:
        if status['active_reset']:
            log("Lap " + str(lap['completed']) + " [Time: N/A | Invalid Lap]")
        elif "Qualify" in session['name'] or "Race" not in session['name'] and gui.Vars.input['practice_laps'] == 0:
            log("Lap " + str(lap['completed']) + " [Time: " + duration(lap['time_prev']) + " | Laps: " + str(round(stint['remaining_prev'], 2)) + " | Used: " + volume(usage['prev'], "short") + " | Eco: " + economy(eco['prev']) + "]")
        else:
            log("Lap " + str(lap['completed']) + " [Time: " + duration(lap['time_prev']) + " | Laps: " + str(round(stint['remaining_prev'], 2)) + " | Used: " + volume(usage['prev'], "short") + " | Usage Req: " + volume(usage['req'], "short") +
                " | Eco: " + economy(eco['prev']) + " | Eco Req: " + economy(eco['req']) + " | Level Req: " + volume(level['req_prev'], "short") + "]")
        status['separator'] = False


# Stint report printed when resetting/pitting
def pit_report():
    if status['pitting'] and trigger['pitting'] or status['towing'] and trigger['towing'] or trigger['car_reset'] or not status['driving'] and trigger['driving'] and session['state'] >= 5:
        if status['towing'] or trigger['car_reset'] or not status['driving']:
            stint['used'] = level['pit'] - level['prev']
        elif level['current'] < level['pit']:
            stint['used'] = level['pit'] - level['current']
        elif level['current'] >= level['pit']:
            stint['used'] = level['pit'] - level['current_prev']
        if stint['completed'] > 0:
            time.sleep(0.8)
            ir.freeze_var_buffer_latest()

            try:
                stint['eco'] = (stint['completed'] * misc['track_length']) / stint['used']
            except ZeroDivisionError:
                stint['eco'] = 0.0
            stint['avg'] = stint['used'] / stint['completed']
            separator()
            log("Lap " + str(lap['completed']) + " Pit Report")
            log(lang['separator_b'])
            log("Stint: " + str(stint['completed']) + " laps" + ", " + "Avg Time: " + duration(stint['time_avg']) + ", " + "Avg Used: " + volume(stint['avg'], "short") + ", " +
                "Avg Eco: " + economy(stint['eco']) + ", " + "Total Used: " + volume(stint['used'], "short"))
            log(lang['separator_a'])
            log("Tire Wear")
            log(lang['separator_b'])
            log("LF: " + percent(ir['LFwearL']) + " " + percent(ir['LFwearM']) + " " + percent(ir['LFwearR']) + "     " +
                "RF: " + percent(ir['RFwearL']) + " " + percent(ir['RFwearM']) + " " + percent(ir['RFwearR']))
            log("")
            log("LR: " + percent(ir['LRwearL']) + " " + percent(ir['LRwearM']) + " " + percent(ir['LRwearR']) + "     " +
                "RR: " + percent(ir['RRwearL']) + " " + percent(ir['RRwearM']) + " " + percent(ir['RRwearR']))
            log(lang['separator_a'])
            log("Tire Temp")
            log(lang['separator_b'])
            log("LF: " + temperature(ir['LFtempCL'], "string") + " " + temperature(ir['LFtempCM'], "string") + " " + temperature(ir['LFtempCR'], "string") + "     " +
                "RF: " + temperature(ir['RFtempCL'], "string") + " " + temperature(ir['RFtempCM'], "string") + " " + temperature(ir['RFtempCR'], "string"))
            log("")
            log("LR: " + temperature(ir['LRtempCL'], "string") + " " + temperature(ir['LRtempCM'], "string") + " " + temperature(ir['LRtempCR'], "string") + "     " +
                "RR: " + temperature(ir['RRtempCL'], "string") + " " + temperature(ir['RRtempCM'], "string") + " " + temperature(ir['RRtempCR'], "string"))
            log(lang['separator_a'])
            status['separator'] = True

            ir.unfreeze_var_buffer_latest()

            reset_vars("stint")


# Log session info
def session_update():
    if trigger['session'] == "Changed" and str(round((weather['temp_track'] * 1.8) + 32, 3)).endswith("0"):
        separator()
        log(session['name'])
        log(lang['separator_b'])
        log("Skies: " + weather['sky'] + ", " + "Air: " + temperature(weather['temp_air'], "string") + ", " + "Surface: " + temperature(weather['temp_track'], "string") + ", " + "Wind: " + weather['wind_dir'] + " @ " + speed(weather['wind_vel']) + ", " +
            "Humidity: " + percent(weather['humidity']) + ", " + "Pressure: " + pressure(weather['pressure']) + ", " + "Density: " + density(weather['density']))
        log(lang['separator_a'])
        status['separator'] = True
        trigger['session'] = "Pause"
        reset_vars(("car", "session", "stint"))
    elif trigger['session'] == "Reset":
        separator()
        log("Session Reset")
        log(lang['separator_a'])
        status['separator'] = True
        trigger['session'] = "Pause"
        reset_vars(("car", "session", "stint"))


# Consolidated environmental temperature updates
def temp_updates():
    if gui.Vars.checkboxes['temp_updates'] and session['time'] > 10.0:
        temp_types = (("air", "Ambient"), ("track", "Surface"))
        for type in temp_types:
            # Check if a change is triggered
            if trigger[type[0]] != "None":
                # Check if the change is an increase or decrease
                if trigger[type[0]] == "Increase":
                    speech = threading.Thread(target=speech_thread, args=(type[0] + " temp has increased to " + str(int(round(temperature(weather['temp_' + type[0]], "number"), 0))) + " degrees",))
                    speech.start()
                elif trigger[type[0]] == "Decrease":
                    speech = threading.Thread(target=speech_thread, args=(type[0] + " temp has decreased to " + str(int(round(temperature(weather['temp_' + type[0]], "number"), 0))) + " degrees",))
                    speech.start()
                separator()
                log(type[1] + ": " + temperature(weather['temp_' + type[0]], "string"))
                log(lang['separator_a'])
                status['separator'] = True


# Text alert for previous lap's fuel info
def txt_prev_lap():
    ir.chat_command(1)
    time.sleep(0.05)
    if gui.Vars.input['practice_laps'] == 0 and status['practice']:
        keyboard.write("## Previous lap - " + str(round(stint['remaining_prev'], 1)) + " laps, " + volume(usage['prev'], "short") + ", " + economy(eco['prev']) + " ##")
    else:
        keyboard.write("## Previous lap - " + str(round(stint['remaining_prev'], 1)) + " laps, " + volume(usage['prev'], "short") + ", " + economy(eco['prev']) + ", " + volume(level['req_prev'], "short") + "(" + str(stops['prev']) + ", " + str(window['prev']) + ") extra ##")
    time.sleep(0.05)
    keyboard.send('enter')
    time.sleep(0.05)
    ir.chat_command(3)


# Print race weekend info
def weekend():
    separator()
    log("Weekend")
    log(lang['separator_b'])
    log("Track: " + misc['track_name'] + ", " + "Car: " + car['name'] + ", " + "Length: " + distance(misc['track_length'], "km") + ", " +
        "Date: " + misc['date'] + " " + misc['time'] + ", " + "Rubber: " + misc['rubber'] + ", " + "Max Fuel: " + percent(level['full_pct']))
    status['separator'] = False


# Various other functions
# Check iRacing connection status and do actions
def check_iracing():
    try:
        if not State.connected and ir.startup() and ir.is_initialized and ir.is_connected:
            # Set connection status
            State.connected = True

            # Give iRacing time to load
            time.sleep(1)

            # Detect user's driver id and determine if they are a spectator or spotter
            uid = drv_info("DriverUserID", 0)
            for idx in range(64, -2, -1):
                try:
                    cid = ir['DriverInfo']['Drivers'][idx]['UserID']
                    if cid == uid:
                        misc['idx'] = idx
                        status['spotter'] = False
                        if drv_info("Drivers", "IsSpectator") == 1:
                            status['spectator'] = True
                        else:
                            status['spectator'] = False
                        break
                    elif idx == -1:
                        misc['idx'] = drv_info("DriverCarIdx", 0)
                        status['spotter'] = True
                except IndexError:
                    pass

            # Call init variable actions
            init_vars()

            # Start connected-only threads
            threading.Thread(target=fueling_thread, daemon=True).start()
            threading.Thread(target=warnings_thread, daemon=True).start()

            # Connected alert
            separator()
            log('iRacing Connected')
            log(lang['separator_a'])
            status['separator'] = True
            speech = threading.Thread(target=speech_thread, args=("Fuel companion connected",))
            speech.start()

            # Needed to "reset" keyboard module for some reason
            keyboard.write("")
        elif State.connected and not (ir.is_initialized and ir.is_connected):
            # Disconnected alert
            separator()
            log('iRacing Disconnected')
            log(lang['separator_a'])
            status['separator'] = True

            # Shut down irsdk
            ir.shutdown()

            # Call deinit variable actions
            deinit_vars()
    except ConnectionResetError:
        pass


# Check for program updates
def check_update():
    if gui.Vars.checkboxes["check_updates"]:
        try:
            with urllib.request.urlopen('https://www.renovamenia.com/files/iracing/other/iR_Fuel_Companion/version.txt') as file:
                server_version = file.read().decode('utf-8').strip("v").split('.')
                local_version = lang['version'].strip("v").split('.')
                if local_version[0] < server_version[0]:
                    available = True
                elif local_version[1] < server_version[1]:
                    if local_version[0] == server_version[0]:
                        available = True
                    else:
                        available = False
                elif local_version[2] < server_version[2]:
                    if local_version[0] == server_version[0] and local_version[1] == server_version[1]:
                        available = True
                    else:
                        available = False
                else:
                    available = False
                if available:
                    threading.Thread(target=speech_thread, args=("Update v" + server_version[0] + "." + server_version[1] + "." + server_version[2] + " available!",)).start()
                    log("Update v" + server_version[0] + "." + server_version[1] + "." + server_version[2] + " available! https://github.com/janewsome63/iR-Fuel-Companion/releases")
                    log(lang['separator_a'])
        except urllib.error.URLError as error:
            log("Update checking failed, cannot connect to update server! " + str(error))
            log(lang['separator_a'])


# Shorten DriverInfo calls
def drv_info(group, subgroup):
    if subgroup == 0:
        return ir['DriverInfo'][group]
    else:
        return ir['DriverInfo'][group][misc['idx']][subgroup]
        # except Exception as ex:
        #    CamIdx = ir['CamCarIdx']
        #    return ir['DriverInfo'][group][CamIdx][subgroup]


# Shorten SessionInfo calls
def session_info(group):
    if State.connected:
        return ir['SessionInfo']['Sessions'][ir['SessionNum']][group]


# Func to not double up on separators because it bothered me
def separator():
    if not status['separator']:
        log(lang['separator_a'])


# TTS thread
def speech_thread(text):
    pythoncom.CoInitialize()
    speech = wincl.Dispatch("SAPI.SpVoice")
    speech.Speak(text)


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


# Variables that need to be set from the SDK
def update_vars():
    ir.freeze_var_buffer_latest()

    # Detect unit type
    if ir['DisplayUnits'] == 0:
        status['imperial'] = True

    # Update live fuel vars
    if ir['FuelLevel'] > 0.0:
        if not car['location'] == 1:
            level['current_prev'] = level['current']
        level['current'] = ir['FuelLevel']
        level['current_pct'] = ir['FuelLevelPct']

    # Update live telem vars
    car['engine_hex'] = ir['EngineWarnings']
    car['location'] = ir['PlayerTrackSurface']  # (-1 = not_in_world, 0 = off_track, 1 = in stall, 2 = approaching_pits, 3 = on_track)
    session['flag_hex'] = ir['SessionFlags']
    session['state'] = ir['SessionState']
    session['time'] = ir['SessionTime']
    session['time_remaining'] = ir['SessionTimeRemain']
    weather['density'] = ir['AirDensity']
    weather['humidity'] = ir['RelativeHumidity']
    weather['pressure'] = ir['AirPressure']
    weather['wind_vel'] = ir['WindVel']

    # Check skybox weather
    if ir['Skies'] == 0:
        weather['sky'] = "Clear"
    elif ir['Skies'] == 1:
        weather['sky'] = "Partly Cloudy"
    elif ir['Skies'] == 2:
        weather['sky'] = "Mostly Cloudy"
    elif ir['Skies'] == 3:
        weather['sky'] = "Overcast"
    else:
        weather['sky'] = "N/A"

    # Determine cardinal wind direction
    wind_deg = ir['WindDir'] * 57.295779513
    if wind_deg >= 337.5 or wind_deg <= 22.5:
        weather['wind_dir'] = "N"
    elif 22.5 < wind_deg < 67.5:
        weather['wind_dir'] = "NE"
    elif 67.5 <= wind_deg <= 112.5:
        weather['wind_dir'] = "E"
    elif 112.5 < wind_deg < 157.5:
        weather['wind_dir'] = "SE"
    elif 157.5 <= wind_deg <= 202.5:
        weather['wind_dir'] = "S"
    elif 202.5 < wind_deg < 247.5:
        weather['wind_dir'] = "SW"
    elif 247.5 <= wind_deg <= 292.5:
        weather['wind_dir'] = "W"
    elif 292.5 < wind_deg < 337.5:
        weather['wind_dir'] = "NW"
    else:
        weather['wind_dir'] = "N/A"

    # Check if lap has changed
    if car['location'] >= 2:
        if ir['LapCompleted'] < lap['next'] - 1 or ir['LapCompleted'] > lap['next'] + 1:
            lap['next'] = ir['LapCompleted'] + 1
        elif ir['LapCompleted'] == lap['next']:
            lap['next'] = lap['next'] + 1
            trigger['lap'] = True
        elif ir['LapCompleted'] == lap['next'] - 1:
            trigger['lap'] = False

    # Check if session has changed
    if session['name'] != session_info("SessionType") or trigger['init']:
        session['name'] = session_info("SessionType")
        trigger['session'] = "Changed"
    elif trigger['session'] == "Changed":
        pass
    elif math.floor(session['time']) == 0.0 and trigger['session'] != "Pause":
        trigger['session'] = "Reset"
    elif math.floor(session['time']) > 0.0 and trigger['session'] == "Pause":
        trigger['session'] = "None"

    # Check if session is practice
    if "Qualify" in session['name'] or "Race" in session['name']:  # Heat and consolation races seem to simply be reported as "Race"
        status['practice'] = False
    else:
        status['practice'] = True

    # Check if caution is out
    if "caution" in session['flag_list']:
        status['caution'] = True
    else:
        status['caution'] = False

    # Check if session is timed
    if ir['SessionLapsRemain'] <= 10000:
        status['timed'] = False
    else:
        status['timed'] = True

    # Set fuel limits
    if status['practice'] or drv_info("DriverCarMaxFuelPct", 0) != 1 and gui.Vars.input['practice_laps'] != 0:
        # Use practice fuel values if max fuel is 100%, else use normal
        level['full_pct'] = gui.Vars.input['practice_fuel_percent'] / 100
        level['full'] = drv_info("DriverCarFuelMaxLtr", 0) * level['full_pct']
    else:
        # Use normal fuel values
        level['full_pct'] = drv_info("DriverCarMaxFuelPct", 0)
        level['full'] = drv_info("DriverCarFuelMaxLtr", 0)

    # Detect if car is being towed
    if ir['PlayerCarTowTime'] > 0.0:
        if not status['towing']:
            status['towing'] = True
            trigger['towing'] = True
        else:
            trigger['towing'] = False
    else:
        if status['towing']:
            status['towing'] = False
            trigger['towing'] = True
        else:
            trigger['towing'] = False

    # Check if car has been reset
    if car['temp_oil'] + car['temp_water'] == 154.0 and car['temp_oil_prev'] + car['temp_water_prev'] != 154.0 and session['time'] > 5.0:
        trigger['car_reset'] = True
    else:
        trigger['car_reset'] = False

    # Check if an active reset happened
    lap['dist_prev'] = lap['dist']
    lap['dist'] = ir['LapDist']
    if not trigger['lap'] and car['location'] != 1 and car['location'] != -1 and "Offline Testing" in session['name']:
        if lap['dist'] > lap['dist_prev'] + 15 or lap['dist'] < lap['dist_prev'] - 15:
            trigger['active_reset'] = True
            status['active_reset'] = True
        else:
            trigger['active_reset'] = False

    # Consolidated status values
    status_types = [("driving", "IsOnTrack"), ("pitting", "PitstopActive")]
    for type in status_types:
        if status[type[0]] != ir[type[1]]:
            status[type[0]] = ir[type[1]]
            trigger[type[0]] = True
        else:
            trigger[type[0]] = False

    # Check if environmental temperatures have changed
    types = [("air", "AirTemp", 0.55), ("track", "TrackTempCrew", 2.0)]
    for type in types:
        if ir[type[1]] > weather['temp_' + type[0] + '_prev'] + type[2]:
            trigger[type[0]] = "Increase"
            weather['temp_' + type[0] + '_prev'] = ir[type[1]]
        elif ir[type[1]] < weather['temp_' + type[0] + '_prev'] - type[2]:
            trigger[type[0]] = "Decrease"
            weather['temp_' + type[0] + '_prev'] = ir[type[1]]
        else:
            trigger[type[0]] = "None"
        weather['temp_' + type[0]] = ir[type[1]]

    # Consolidated temperature updates
    types = [("oil", "OilTemp"), ("water", "WaterTemp")]
    for type in types:
        car['temp_' + type[0] + '_prev'] = car['temp_' + type[0]]
        car['temp_' + type[0]] = ir[type[1]]

    ir.unfreeze_var_buffer_latest()

    # Driving status changed
    if trigger['driving'] and status['driving'] or trigger['car_reset']:
        misc['timer_start'] = time.perf_counter()
        lap['pit'] = lap['completed']
        level['pit'] = level['current']

    # Pitting status changed
    if trigger['pitting']:
        if not status['pitting']:
            lap['pit'] = lap['completed']
            level['pit'] = level['current']

    # Actions to do if car was reset to box
    if trigger['car_reset'] and not trigger['init']:
        separator()
        log("Car Reset")
        log(lang['separator_a'])
        status['separator'] = True
        if status['practice']:
            reset_vars("car")

    # Actions to do if an active reset happened
    if trigger['active_reset']:
        separator()
        log("Active Reset")
        log(lang['separator_a'])
        status['separator'] = True
        if status['practice']:
            reset_vars("active")

    # Things to do on first connect
    if trigger['init']:
        if status['spectator']:
            separator()
            log("Spectator Mode")
            log(lang['separator_a'])
            status['separator'] = True
        elif status['spotter']:
            separator()
            log("Spotter Mode")
            log(lang['separator_a'])
            status['separator'] = True
        weekend()
        trigger['init'] = False

    # Lap completion telemetry, needs a slight delay and reset of the buffer in order to properly update
    if trigger['lap']:
        time.sleep(0.8)
        ir.freeze_var_buffer_latest()

        # Check if lap had an incident
        misc['incidents_prev'] = misc['incidents']
        misc['incidents'] = ir['PlayerCarMyIncidentCount']
        if misc['incidents'] > misc['incidents_prev']:
            status['incident'] = True
        else:
            status['incident'] = False

        # Set previous lap time
        if ir['LapLastLapTime'] <= 0 or ir['LapLastLapTime'] == lap['time_prev']:
            lap['time_prev'] = time.perf_counter() - misc['timer_start']
        else:
            lap['time_prev'] = ir['LapLastLapTime']
        misc['timer_start'] = time.perf_counter()

        if ir['LapCompleted'] > 0:
            # Set laps completed
            if status['practice'] and gui.Vars.input['practice_laps'] != 0:
                lap['completed'] = lap['completed'] + 1
            else:
                lap['completed'] = ir['LapCompleted']

            if not status['incident'] and not status['caution'] and not status['active_reset']:
                # Overall average lap times
                lap['times'].append(lap['time_prev'])
                total = 0
                for entry in lap['times']:
                    total = total + entry
                lap['time_avg'] = total / len(lap['times'])

                # Stint average lap times
                stint['times'].append(lap['time_prev'])
                total = 0
                for entry in stint['times']:
                    total = total + entry
                stint['time_avg'] = total / len(stint['times'])

        # Determine total and remaining laps
        if status['practice'] and gui.Vars.input['practice_laps'] != 0:
            lap['total'] = gui.Vars.input['practice_laps']
            lap['remaining'] = gui.Vars.input['practice_laps'] - lap['completed']
        elif status['timed'] and lap['time_avg'] > 0:
            lap['total'] = math.ceil(session['time_total'] / lap['time_avg'])
            lap['remaining'] = math.ceil(session['time_remaining'] / lap['time_avg'])
        elif status['timed'] and lap['time_avg'] <= 0:
            lap['total'] = math.ceil(session['time_total'] / (misc['track_length'] / 0.5))
            lap['remaining'] = math.ceil(session['time_remaining'] / (misc['track_length'] / 0.5)) - lap['completed']
        else:
            lap['total'] = ir['SessionLapsTotal']
            if (ir['SessionLapsRemain'] + 1) < 0:
                lap['remaining'] = 0
            else:
                lap['remaining'] = ir['SessionLapsRemain'] + 1

        fuel_calc()

        lap_alerts()

        # Set lap completion variables
        stint['completed'] = stint['completed'] + 1
        level['prev'] = level['current']

        reset_vars("lap")

        ir.unfreeze_var_buffer_latest()


# Main loop (run in thread because the GUI technically needs to be the "main" loop)
def main():
    # Has to pause or the GUI gets mad
    time.sleep(1)

    # Launch message
    log("iR Fuel Companion " + lang['version'])
    log(lang['separator_a'])

    check_update()

    # Check for iR connection and do functions every cycle
    try:
        while True:
            check_iracing()
            if State.connected:
                update_vars()
                session_update()
                temp_updates()
                engine_warnings()
                pit_report()
            # Delay (min 1/60)
            time.sleep(1 / 15)
    except KeyboardInterrupt:
        pass


# Set date
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
    ir = irsdk.IRSDK()
    if not os.path.exists(gui.Vars.user_dir + '\\settings.ini'):
        gui.set_config()
    read_config()
    tts = wincl.Dispatch("SAPI.SpVoice")
    # threading.Thread(target=keybind.gamepad, daemon=True).start()
    threading.Thread(target=keybind.keys, daemon=True).start()
    threading.Thread(target=controls_thread, daemon=True).start()
    threading.Thread(target=binding_thread, daemon=True).start()
    threading.Thread(target=main, daemon=True).start()

    gui.main(lang['version'])
