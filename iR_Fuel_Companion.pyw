#!python3

import irsdk
import reg
import time
import os
import subprocess
import sys
import keyboard
import threading
import pythoncom
import PySimpleGUI as sg
import win32com.client as wincl
import math
from datetime import datetime

# Random variables
class State:
    version = "v0.1.3"
    reg_path = 'Software\\iR Fuel Companion'
    sep_1 = "=" * 135
    sep_2 = "-" * 135
    metric = True
    ir_connected = False
    trigger = False
    count = 1
    print_sep = True
    fuel_read = 1
    auto_fuel = 1
    fuel_max = 0
    fuel_pad = 2
    practice_laps = 0
    practice_fuelpct = 100
    reset_laps = 0
    surface = -1

# Variables and functions for units and conversion
# For ref: l * 0.264172 = gal | km * 0.621371 = mi | m * 0.000621371 = mi | (c * 1.8) + 32 = f | kph * 0.6213711922 = mph | rad * 57.295779513 = deg | m/s * 2.2369362920544025 = mph | Hg * 3.38639 = kPa | kg/m^3 * 0.062427960576145 = lb/ft^3 | km/l * 2.352145833 = mpg
class Units:
    # Detect in-game unit system
    def detect(self):
        if ir['DisplayUnits'] == 1:
            state.metric = True
        elif ir['DisplayUnits'] == 0:
            state.metric = False

    # Return a cardinal wind direction
    def wind_dir(self):
        wind_deg = ir['WindDir'] * 57.295779513
        wind_card = "N/A"
        if wind_deg >= 337.5 or wind_deg <= 22.5:
            wind_card = "N"
        elif wind_deg > 22.5 and wind_deg < 67.5:
            wind_card = "NE"
        elif wind_deg >= 67.5 and wind_deg <= 112.5:
            wind_card = "E"
        elif wind_deg > 112.5 and wind_deg < 157.5:
            wind_card = "SE"
        elif wind_deg >= 157.5 and wind_deg <= 202.5:
            wind_card = "S"
        elif wind_deg > 202.5 and wind_deg < 247.5:
            wind_card = "SW"
        elif wind_deg >= 247.5 and wind_deg <= 292.5:
            wind_card = "W"
        elif wind_deg > 292.5 and wind_deg < 337.5:
            wind_card = "NW"
        return wind_card

    # Percent formatting
    def pct(self, value):
        pct_result = str(round(value * 100, 2)) + "%"
        return pct_result

    # Time formatting
    def time(self, value):
        time_result = str(round(value, 3)) + "s"
        return time_result

    # Temperature
    def temp(self, value):
        if state.metric == True:
            temp_result = str(round(value, 2)) + "c"
        elif state.metric == False:
            temp_result = str(round((value * 1.8) + 32, 2)) + "f"
        return temp_result

    # Speed
    def speed(self, value):
        if state.metric == True:
            speed_result = str(round(value * 3.6, 1)) + "kph"
        elif state.metric == False:
            speed_result = str(round(value * 2.2369362920544025, 1)) + "mph"
        return speed_result

    # Pressure
    def press(self, value):
        if state.metric == True:
            press_result = str(round(value * 3.38639, 1)) + "kpa"
        elif state.metric == False:
            press_result = str(round(value, 1)) + "hg"
        return press_result

    # Density
    def dens(self, value):
        if state.metric == True:
            dens_result = str(round(value, 2)) + "kg/m^3"
        elif state.metric == False:
            dens_result = str(round(value * 0.062427960576145, 2)) + "lb/ft^3"
        return dens_result

    # Distance
    def dist(self, value, toggle):
        if toggle == "m":
            if state.metric == True:
                dist_result = str(round(value * 0.001, 2)) + "km"
            elif state.metric == False:
                dist_result = str(round(value * 0.000621371, 2)) + "mi"
        elif toggle == "km":
            if state.metric == True:
                dist_result = str(round(value, 2)) + "km"
            elif state.metric == False:
                dist_result = str(round(value * 0.621371, 2)) + "mi"
        return dist_result

    # Volume
    def vol(self, value, toggle):
        if toggle == "abv":
            if state.metric == True:
                vol_result = str(round(value, 3)) + "l"
            elif state.metric == False:
                vol_result = str(round(value * 0.264172, 3)) + "gal"
        elif toggle == "full":
            if state.metric == True:
                vol_result = str(round(value, 3)) + " liters"
            elif state.metric == False:
                vol_result = str(round(value * 0.264172, 3)) + " gallons"
        return vol_result

    # Fuel economy
    def econ(self, value):
        if state.metric == True:
            econ_result = str(round(value, 2)) + "km/l"
        elif state.metric == False:
            econ_result = str(round(value * 2.352145833, 2)) + "mpg"
        return econ_result

# Fuel variables
class Fuel:
    level = 0.0
    pct = 0.0
    max_pct = 0.0
    level_full = 0.0
    last_level = 0.0
    used_lap = 0.0
    used_lap_avg = 0.0
    used_lap_max = 0.0
    used_lap_list = []
    used_lap_req = 0.0
    laps_left = 0.0
    eco = 0.0
    eco_req = 0.0
    level_req = 0.0
    level_req_max = 0.0
    level_req_avg = 0.0
    stint_used = 0.0
    stint_used_avg = 0.0
    stint_eco = 0.0
    last_pit_level = 0.0
    stops = 0
    stops_avg = 0
    stops_max = 0

# Other iR telemetry variables
class Telem:
    laps_completed = 0
    laps_remaining = 0
    lap_distance = 0
    driver_idx = 0
    session = 0
    location = 1
    stint_laps = 0
    last_ttemp = 0.0
    flag = "0x00000000"
    flag_list = []
    lap_time_list = []

# Open program
def StartProgram(program):
    #SW_HIDE = 0
    #SW_MINIMIZE = 6
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    #si.wShowWindow = SW_HIDE
    #si.wShowWindow = SW_MINIMIZE
    subprocess.Popen(program, startupinfo=si)

def GetRegistry():
    if reg.get_reg(state.reg_path, 'Read'):
        state.fuel_read = reg.get_reg(state.reg_path, 'Read')
    if reg.get_reg(state.reg_path, 'Auto'):
        state.auto_fuel = reg.get_reg(state.reg_path, 'Auto')
    if reg.get_reg(state.reg_path, 'Max'):
        state.fuel_max = reg.get_reg(state.reg_path, 'Max')
    if reg.get_reg(state.reg_path, 'Pad'):
        state.fuel_pad = reg.get_reg(state.reg_path, 'Pad')
    if reg.get_reg(state.reg_path, 'Laps'):
        state.practice_laps = reg.get_reg(state.reg_path, 'Laps')
    if reg.get_reg(state.reg_path, 'Pct'):
        state.practice_fuelpct = reg.get_reg(state.reg_path, 'Pct')
    SetRegistry()

def SetRegistry():
    reg.set_reg(state.reg_path, 'Read', state.fuel_read)
    reg.set_reg(state.reg_path, 'Auto', state.auto_fuel)
    reg.set_reg(state.reg_path, 'Max', state.fuel_max)
    reg.set_reg(state.reg_path, 'Pad', state.fuel_pad)
    reg.set_reg(state.reg_path, 'Laps', state.practice_laps)
    reg.set_reg(state.reg_path, 'Pct', state.practice_fuelpct)

def SpeechThread(speech):
    pythoncom.CoInitialize()
    tts = wincl.Dispatch("SAPI.SpVoice")
    tts.Speak(speech)

# Hotkeys for various text/toggles
def KeysThread():
    while True:
        if keyboard.is_pressed('ctrl+shift+f1') == True:
            time.sleep(0.25)
            ir.chat_command(1)
            time.sleep(0.05)
            keyboard.write("## Current pace - " + str(round(fuel.laps_left, 2)) + " laps, " + units.vol(fuel.used_lap, "abv") + ", " + units.econ(fuel.eco) + ", " + units.vol(fuel.level_req, "abv") + "(" + str(fuel.stops) + ") extra ##")
            time.sleep(0.05)
            keyboard.send('enter')
            time.sleep(0.05)
            ir.chat_command(3)
            time.sleep(0.75)
        if keyboard.is_pressed('ctrl+shift+f2') == True:
            time.sleep(0.25)
            ir.chat_command(1)
            time.sleep(0.05)
            keyboard.write("## To finish - " + str(telem.laps_remaining) + " laps, " + units.vol(fuel.used_lap_req, "abv") + ", " + units.econ(fuel.eco_req) + ", " + units.vol(fuel.level_req_avg, "abv") + "(" + str(fuel.stops_avg) + ") avg, " + units.vol(fuel.level_req_max, "abv") + "(" + str(fuel.stops_max) + ") max ##")
            time.sleep(0.05)
            keyboard.send('enter')
            time.sleep(0.05)
            ir.chat_command(3)
            time.sleep(0.75)
        if keyboard.is_pressed('ctrl+shift+f3') == True:
            time.sleep(0.25)
            if state.fuel_max == 1:
                state.fuel_max = 0
                SetRegistry()
                speech_thread = threading.Thread(target=SpeechThread, args=("using average fuel usage for auto fuel",))
                speech_thread.start()
            elif state.fuel_max == 0:
                state.fuel_max = 1
                SetRegistry()
                speech_thread = threading.Thread(target=SpeechThread, args=("using max fuel usage for auto fuel",))
                speech_thread.start()
            time.sleep(0.75)
        if keyboard.is_pressed('ctrl+shift+f4') == True:
            time.sleep(0.25)
            if state.fuel_read == 1:
                state.fuel_read = 0
                SetRegistry()
                speech_thread = threading.Thread(target=SpeechThread, args=("fuel reading disabled",))
                speech_thread.start()
            elif state.fuel_read == 0:
                state.fuel_read =  1
                SetRegistry()
                speech_thread = threading.Thread(target=SpeechThread, args=("fuel reading enabled",))
                speech_thread.start()
            time.sleep(0.75)
        if keyboard.is_pressed('ctrl+shift+f5') == True:
            time.sleep(0.25)
            if state.auto_fuel == 1:
                state.auto_fuel = 0
                SetRegistry()
                speech_thread = threading.Thread(target=SpeechThread, args=("auto fuel disabled",))
                speech_thread.start()
            elif state.auto_fuel == 0:
                state.auto_fuel =  1
                SetRegistry()
                speech_thread = threading.Thread(target=SpeechThread, args=("auto fuel enabled",))
                speech_thread.start()
            time.sleep(0.75)
        if keyboard.is_pressed('ctrl+shift+f6') == True:
            time.sleep(0.25)
            FuelAdd = fuel.level_req_avg + (fuel.used_lap_avg * state.fuel_pad)
            if state.fuel_max == 1:
                FuelAdd = fuel.level_req_max + (fuel.used_lap_max * state.fuel_pad)
            if FuelAdd + fuel.last_level <= ir['FuelLevel']:
                ir.pit_command(11)
            if FuelAdd + fuel.last_level > ir['FuelLevel']:
                ir.pit_command(2, int(round(FuelAdd, 0)))
            time.sleep(0.75)
        time.sleep(1/60)

# Return driver flag
def Flags():
        # Flag codes
        # checkered        = 0x00000001
        # white            = 0x00000002
        # green            = 0x00000004
        # yellow           = 0x00000008

        # red              = 0x00000010
        # blue             = 0x00000020
        # debris           = 0x00000040
        # crossed          = 0x00000080

        # yellow_waving    = 0x00000100
        # one_lap_to_green = 0x00000200
        # green_held       = 0x00000400
        # ten_to_go        = 0x00000800

        # five_to_go       = 0x00001000
        # random_waving    = 0x00002000
        # caution          = 0x00004000
        # caution_waving   = 0x00008000

        # black            = 0x00010000
        # disqualify       = 0x00020000
        # servicible       = 0x00040000
        # furled           = 0x00080000

        # repair           = 0x00100000

        # start_hidden     = 0x10000000
        # start_ready      = 0x20000000
        # start_set        = 0x40000000
        # start_go         = 0x80000000

    while True:
        telem.flag_list = []

        # First digit
        if telem.flag[-1] == "1":
            telem.flag_list.append("checkered")
        elif telem.flag[-1] == "2":
            telem.flag_list.append("white")
        elif telem.flag[-1] == "3":
            telem.flag_list.append("checkered")
            telem.flag_list.append("white")
        elif telem.flag[-1] == "4":
            telem.flag_list.append("green")
        elif telem.flag[-1] == "5":
            telem.flag_list.append("checkered")
            telem.flag_list.append("green")
        elif telem.flag[-1] == "6":
            telem.flag_list.append("white")
            telem.flag_list.append("green")
        elif telem.flag[-1] == "7":
            telem.flag_list.append("checkered")
            telem.flag_list.append("white")
            telem.flag_list.append("green")
        elif telem.flag[-1] == "8":
            telem.flag_list.append("yellow")
        elif telem.flag[-1] == "9":
            telem.flag_list.append("checkered")
            telem.flag_list.append("yellow")
        elif telem.flag[-1] == "a":
            telem.flag_list.append("white")
            telem.flag_list.append("yellow")
        elif telem.flag[-1] == "b":
            telem.flag_list.append("checkered")
            telem.flag_list.append("white")
            telem.flag_list.append("yellow")
        elif telem.flag[-1] == "c":
            telem.flag_list.append("green")
            telem.flag_list.append("yellow")
        elif telem.flag[-1] == "d":
            telem.flag_list.append("checkered")
            telem.flag_list.append("green")
            telem.flag_list.append("yellow")
        elif telem.flag[-1] == "e":
            telem.flag_list.append("white")
            telem.flag_list.append("green")
            telem.flag_list.append("yellow")
        elif telem.flag[-1] == "f":
            telem.flag_list.append("checkered")
            telem.flag_list.append("white")
            telem.flag_list.append("green")
            telem.flag_list.append("yellow")

        # Second digit
        if telem.flag[-2] == "1":
            telem.flag_list.append("red")
        elif telem.flag[-2] == "2":
            telem.flag_list.append("blue")
        elif telem.flag[-2] == "3":
            telem.flag_list.append("red")
            telem.flag_list.append("blue")
        elif telem.flag[-2] == "4":
            telem.flag_list.append("debris")
        elif telem.flag[-2] == "5":
            telem.flag_list.append("red")
            telem.flag_list.append("debris")
        elif telem.flag[-2] == "6":
            telem.flag_list.append("blue")
            telem.flag_list.append("debris")
        elif telem.flag[-2] == "7":
            telem.flag_list.append("red")
            telem.flag_list.append("blue")
            telem.flag_list.append("debris")
        elif telem.flag[-2] == "8":
            telem.flag_list.append("crossed")
        elif telem.flag[-2] == "9":
            telem.flag_list.append("red")
            telem.flag_list.append("crossed")
        elif telem.flag[-2] == "a":
            telem.flag_list.append("blue")
            telem.flag_list.append("crossed")
        elif telem.flag[-2] == "b":
            telem.flag_list.append("red")
            telem.flag_list.append("blue")
            telem.flag_list.append("crossed")
        elif telem.flag[-2] == "c":
            telem.flag_list.append("debris")
            telem.flag_list.append("crossed")
        elif telem.flag[-2] == "d":
            telem.flag_list.append("red")
            telem.flag_list.append("debris")
            telem.flag_list.append("crossed")
        elif telem.flag[-2] == "e":
            telem.flag_list.append("blue")
            telem.flag_list.append("debris")
            telem.flag_list.append("crossed")
        elif telem.flag[-2] == "f":
            telem.flag_list.append("red")
            telem.flag_list.append("blue")
            telem.flag_list.append("debris")
            telem.flag_list.append("crossed")

        # Third digit
        if telem.flag[-3] == "1":
            telem.flag_list.append("yellow_waving")
        elif telem.flag[-3] == "2":
            telem.flag_list.append("one_lap_to_green")
        elif telem.flag[-3] == "3":
            telem.flag_list.append("yellow_waving")
            telem.flag_list.append("one_lap_to_green")
        elif telem.flag[-3] == "4":
            telem.flag_list.append("green_held")
        elif telem.flag[-3] == "5":
            telem.flag_list.append("yellow_waving")
            telem.flag_list.append("green_held")
        elif telem.flag[-3] == "6":
            telem.flag_list.append("one_lap_to_green")
            telem.flag_list.append("green_held")
        elif telem.flag[-3] == "7":
            telem.flag_list.append("yellow_waving")
            telem.flag_list.append("one_lap_to_green")
            telem.flag_list.append("green_held")
        elif telem.flag[-3] == "8":
            telem.flag_list.append("ten_to_go")
        elif telem.flag[-3] == "9":
            telem.flag_list.append("yellow_waving")
            telem.flag_list.append("ten_to_go")
        elif telem.flag[-3] == "a":
            telem.flag_list.append("one_lap_to_green")
            telem.flag_list.append("ten_to_go")
        elif telem.flag[-3] == "b":
            telem.flag_list.append("yellow_waving")
            telem.flag_list.append("one_lap_to_green")
            telem.flag_list.append("ten_to_go")
        elif telem.flag[-3] == "c":
            telem.flag_list.append("green_held")
            telem.flag_list.append("ten_to_go")
        elif telem.flag[-3] == "d":
            telem.flag_list.append("yellow_waving")
            telem.flag_list.append("green_held")
            telem.flag_list.append("ten_to_go")
        elif telem.flag[-3] == "e":
            telem.flag_list.append("one_lap_to_green")
            telem.flag_list.append("green_held")
            telem.flag_list.append("ten_to_go")
        elif telem.flag[-3] == "f":
            telem.flag_list.append("yellow_waving")
            telem.flag_list.append("one_lap_to_green")
            telem.flag_list.append("green_held")
            telem.flag_list.append("ten_to_go")

        # Forth digit
        if telem.flag[-4] == "1":
            telem.flag_list.append("five_to_go")
        elif telem.flag[-4] == "2":
            telem.flag_list.append("random_waving")
        elif telem.flag[-4] == "3":
            telem.flag_list.append("five_to_go")
            telem.flag_list.append("random_waving")
        elif telem.flag[-4] == "4":
            telem.flag_list.append("caution")
        elif telem.flag[-4] == "5":
            telem.flag_list.append("five_to_go")
            telem.flag_list.append("caution")
        elif telem.flag[-4] == "6":
            telem.flag_list.append("random_waving")
            telem.flag_list.append("caution")
        elif telem.flag[-4] == "7":
            telem.flag_list.append("five_to_go")
            telem.flag_list.append("random_waving")
            telem.flag_list.append("caution")
        elif telem.flag[-4] == "8":
            telem.flag_list.append("caution_waving")
        elif telem.flag[-4] == "9":
            telem.flag_list.append("five_to_go")
            telem.flag_list.append("caution_waving")
        elif telem.flag[-4] == "a":
            telem.flag_list.append("random_waving")
            telem.flag_list.append("caution_waving")
        elif telem.flag[-4] == "b":
            telem.flag_list.append("five_to_go")
            telem.flag_list.append("random_waving")
            telem.flag_list.append("caution_waving")
        elif telem.flag[-4] == "c":
            telem.flag_list.append("caution")
            telem.flag_list.append("caution_waving")
        elif telem.flag[-4] == "d":
            telem.flag_list.append("five_to_go")
            telem.flag_list.append("caution")
            telem.flag_list.append("caution_waving")
        elif telem.flag[-4] == "e":
            telem.flag_list.append("random_waving")
            telem.flag_list.append("caution")
            telem.flag_list.append("caution_waving")
        elif telem.flag[-4] == "f":
            telem.flag_list.append("five_to_go")
            telem.flag_list.append("random_waving")
            telem.flag_list.append("caution")
            telem.flag_list.append("caution_waving")

        # Fifth digit
        if telem.flag[-5] == "1":
            telem.flag_list.append("black")
        elif telem.flag[-5] == "2":
            telem.flag_list.append("disqualify")
        elif telem.flag[-5] == "3":
            telem.flag_list.append("black")
            telem.flag_list.append("disqualify")
        elif telem.flag[-5] == "4":
            telem.flag_list.append("servicible")
        elif telem.flag[-5] == "5":
            telem.flag_list.append("black")
            telem.flag_list.append("servicible")
        elif telem.flag[-5] == "6":
            telem.flag_list.append("disqualify")
            telem.flag_list.append("servicible")
        elif telem.flag[-5] == "7":
            telem.flag_list.append("black")
            telem.flag_list.append("disqualify")
            telem.flag_list.append("servicible")
        elif telem.flag[-5] == "8":
            telem.flag_list.append("furled")
        elif telem.flag[-5] == "9":
            telem.flag_list.append("black")
            telem.flag_list.append("furled")
        elif telem.flag[-5] == "a":
            telem.flag_list.append("disqualify")
            telem.flag_list.append("furled")
        elif telem.flag[-5] == "b":
            telem.flag_list.append("black")
            telem.flag_list.append("disqualify")
            telem.flag_list.append("furled")
        elif telem.flag[-5] == "c":
            telem.flag_list.append("servicible")
            telem.flag_list.append("furled")
        elif telem.flag[-5] == "d":
            telem.flag_list.append("black")
            telem.flag_list.append("servicible")
            telem.flag_list.append("furled")
        elif telem.flag[-5] == "e":
            telem.flag_list.append("disqualify")
            telem.flag_list.append("servicible")
            telem.flag_list.append("furled")
        elif telem.flag[-5] == "f":
            telem.flag_list.append("black")
            telem.flag_list.append("disqualify")
            telem.flag_list.append("servicible")
            telem.flag_list.append("furled")

        # Sixth digit
        if telem.flag[-6] == "1":
            telem.flag_list.append("repair")

        # Eighth digit
        if telem.flag[-8] == "1":
            telem.flag_list.append("start_hidden")
        elif telem.flag[-8] == "2":
            telem.flag_list.append("start_ready")
        elif telem.flag[-8] == "3":
            telem.flag_list.append("start_hidden")
            telem.flag_list.append("start_ready")
        elif telem.flag[-8] == "4":
            telem.flag_list.append("start_set")
        elif telem.flag[-8] == "5":
            telem.flag_list.append("start_hidden")
            telem.flag_list.append("start_set")
        elif telem.flag[-8] == "6":
            telem.flag_list.append("start_ready")
            telem.flag_list.append("start_set")
        elif telem.flag[-8] == "7":
            telem.flag_list.append("start_hidden")
            telem.flag_list.append("start_ready")
            telem.flag_list.append("start_set")
        elif telem.flag[-8] == "8":
            telem.flag_list.append("start_go")
        elif telem.flag[-8] == "9":
            telem.flag_list.append("start_hidden")
            telem.flag_list.append("start_go")
        elif telem.flag[-8] == "a":
            telem.flag_list.append("start_ready")
            telem.flag_list.append("start_go")
        elif telem.flag[-8] == "b":
            telem.flag_list.append("start_hidden")
            telem.flag_list.append("start_ready")
            telem.flag_list.append("start_go")
        elif telem.flag[-8] == "c":
            telem.flag_list.append("start_set")
            telem.flag_list.append("start_go")
        elif telem.flag[-8] == "d":
            telem.flag_list.append("start_hidden")
            telem.flag_list.append("start_set")
            telem.flag_list.append("start_go")
        elif telem.flag[-8] == "e":
            telem.flag_list.append("start_ready")
            telem.flag_list.append("start_set")
            telem.flag_list.append("start_go")
        elif telem.flag[-8] == "f":
            telem.flag_list.append("start_hidden")
            telem.flag_list.append("start_ready")
            telem.flag_list.append("start_set")
            telem.flag_list.append("start_go")
        time.sleep(1)

# Fuel calculations
def FuelCalc():
        if fuel.level_full == 0.0:
            fuel.level_full = fuel.level / fuel.pct
        if telem.laps_remaining > 0:
            fuel.used_lap_req = fuel.level / telem.laps_remaining
        else:
            fuel.used_lap_req = 0.000
        fuel.used_lap = fuel.last_level - fuel.level
        if fuel.used_lap < 0:
            fuel.used_lap = fuel.last_pit_level - fuel.level
        if fuel.used_lap > 0:
            fuel.laps_left = fuel.level / fuel.used_lap
            fuel.eco = telem.lap_distance / fuel.used_lap
        else:
            fuel.laps_left = 999.00
            fuel.eco = 99.00
        fuel.eco_req = (telem.lap_distance * telem.laps_remaining) / fuel.level
        if ir['CarIdxPaceLine'][telem.driver_idx] == -1 and ir['CarIdxTrackSurface'][telem.driver_idx] == 3 and ir['SessionState'] == 4 and telem.stint_laps > 1:
            if len(fuel.used_lap_list) >= 5:
                fuel.used_lap_list.pop(0)
            fuel.used_lap_list.append(fuel.used_lap)
            if len(fuel.used_lap_list) > 0:
                total = 0
                for used in fuel.used_lap_list:
                    total = total + used
                fuel.used_lap_avg = total / len(fuel.used_lap_list)
            if fuel.used_lap > fuel.used_lap_max:
                fuel.used_lap_max = fuel.used_lap
        fuel.level_req = ((telem.laps_remaining * fuel.used_lap) - fuel.level)
        if fuel.level_req < 0:
            fuel.level_req = 0.0
        fuel.level_req_avg = ((telem.laps_remaining * fuel.used_lap_avg) - fuel.level)
        if fuel.level_req_avg < 0:
            fuel.level_req_avg = 0.0
        fuel.level_req_max = ((telem.laps_remaining * fuel.used_lap_max) - fuel.level)
        if fuel.level_req_max < 0:
            fuel.level_req_max = 0.0

        fuel.stops = math.ceil(fuel.level_req / (fuel.level_full * fuel.max_pct))
        if fuel.stops < 0:
            fuel.stops = 0
        fuel.stops_avg = math.ceil(fuel.level_req_avg / (fuel.level_full * fuel.max_pct))
        if fuel.stops_avg < 0:
            fuel.stops_avg = 0
        fuel.stops_max = math.ceil(fuel.level_req_max / (fuel.level_full * fuel.max_pct))
        if fuel.stops_max < 0:
            fuel.stops_max = 0

def FuelingThread():
    Pitting = True
    PittingChgd = True
    while True:
        while SessInfo("SessionType") == "Race" and state.auto_fuel == 1 and state.ir_connected == True:
            if "caution" in telem.flag_list:
                FlagChk = True
            elif "caution_waving" in telem.flag_list:
                FlagChk = True
            elif "yellow" in telem.flag_list:
                FlagChk = True
            elif "yellow_waving" in telem.flag_list:
                FlagChk = True
            elif "black" in telem.flag_list:
                FlagChk = False
            else:
                FlagChk = True
            if Pitting == True and PittingChgd == True and FlagChk == True:
                FuelAdd = fuel.level_req_avg + (fuel.used_lap_avg * state.fuel_pad)
                if state.fuel_max == 1:
                    FuelAdd = fuel.level_req_max + (fuel.used_lap_max * state.fuel_pad)
                if FuelAdd + fuel.last_level <= ir['FuelLevel']:
                    ir.pit_command(11)
                if FuelAdd + fuel.last_level > ir['FuelLevel']:
                    ir.pit_command(2, int(round(FuelAdd, 0)))
                    while ir['CarIdxTrackSurface'][telem.driver_idx] == 1:
                        if FuelAdd + fuel.last_level <= ir['FuelLevel']:
                            ir.pit_command(11)
                            break
                        time.sleep(1/60)
                PittingChgd = False
            if ir['CarIdxTrackSurface'][telem.driver_idx] == 1:
                Pitting = True
            else:
                Pitting = False
            if PittingChgd == Pitting:
                PittingChgd = True
            FlagChk = False
            time.sleep(1/60)
        time.sleep(1/5)

def PitReport():
    if fuel.stint_used > 0:
        fuel.stint_used_avg = fuel.stint_used / telem.stint_laps
        fuel.stint_eco = (telem.stint_laps * telem.lap_distance) / fuel.stint_used
    else:
        fuel.stint_used_avg = 0
        fuel.stint_eco = 0
    AvgTime = "N/A"
    if len(telem.lap_time_list) > 0:
        avg = 0
        for lap in telem.lap_time_list:
            avg = avg + lap
        AvgTime = units.time(avg / len(telem.lap_time_list))
    ir.unfreeze_var_buffer_latest()
    PrintSep()
    print("Lap", ir['LapCompleted'] + 1, "Pit Report")
    print(state.sep_2)
    print("Stint: " + str(telem.stint_laps) + " laps", "Avg Time: " + AvgTime, "Avg Used: " + units.vol(fuel.stint_used_avg, "abv"), "Avg Eco: " + units.econ(fuel.stint_eco), "Total Used: " + units.vol(fuel.stint_used, "abv"), sep=', ')
    print(state.sep_1)
    print("Tire Wear")
    print(state.sep_2)
    print("LF: ", units.pct(ir['LFwearL']), units.pct(ir['LFwearM']), units.pct(ir['LFwearR']), "     ", "RF: ", units.pct(ir['RFwearL']), units.pct(ir['RFwearM']), units.pct(ir['RFwearR']))
    print("")
    print("LR: ", units.pct(ir['LRwearL']), units.pct(ir['LRwearM']), units.pct(ir['LRwearR']), "     ", "RR: ", units.pct(ir['RRwearL']), units.pct(ir['RRwearM']), units.pct(ir['RRwearR']))
    print(state.sep_1)
    print("Tire Temp")
    print(state.sep_2)
    print("LF: ", units.temp(ir['LFtempCL']), units.temp(ir['LFtempCM']), units.temp(ir['LFtempCR']), "     ", "RF: ", units.temp(ir['RFtempCL']), units.temp(ir['RFtempCM']), units.temp(ir['RFtempCR']))
    print("")
    print("LR: ", units.temp(ir['LRtempCL']), units.temp(ir['LRtempCM']), units.temp(ir['LRtempCR']), "     ", "RR: ", units.temp(ir['RRtempCL']), units.temp(ir['RRtempCM']), units.temp(ir['RRtempCR']))
    print(state.sep_1)
    state.print_sep = True
    telem.stint_laps = 0
    fuel.stint_used = 0.0
    telem.lap_time_list = []

# Shorten DriverInfo calls
def DrvInfo(group, subgroup):
    if subgroup == 0:
        return ir['DriverInfo'][group]
    else:
        return ir['DriverInfo'][group][telem.driver_idx][subgroup]

# Shorten WeekendInfo calls (and also split string)
def WkndInfo(group, n):
    Result = ir['WeekendInfo'][group]
    ResultSplt = Result.split()
    return ResultSplt[n]

# Shorten WeekendOptions calls (and also split string)
def WkndOpt(group, n):
    Result = ir['WeekendInfo']['WeekendOptions'][group]
    ResultSplt = Result.split()
    return ResultSplt[n]

# Shorten SessionInfo calls
def SessInfo(group):
    if state.ir_connected == True:
        return ir['SessionInfo']['Sessions'][ir['SessionNum']][group]

# Return sky status
def Sky():
    SkyNum = ir['Skies']
    Skies = "N/A"
    if SkyNum == 0:
        Skies = "Clear"
    elif SkyNum == 1:
        Skies = "Partly Cloudy"
    elif SkyNum == 2:
        Skies = "Mostly Cloudy"
    elif SkyNum == 3:
        Skies = "Overcast"
    return Skies

# Func to not double up on seperators because it bothered me
def PrintSep():
    if state.print_sep == False:
        print(state.sep_1)

# Print session info
def Session():
        time.sleep(2)
        PrintSep()
        print(SessInfo("SessionType"))
        print(state.sep_2)
        print("Skies: " + Sky(), "Air: " + units.temp(ir['AirTemp']), "Surface: " + units.temp(ir['TrackTempCrew']), "Wind: " + units.wind_dir() + " @ " + units.speed(ir['WindVel']), "Humidity: " + units.pct(ir['RelativeHumidity']), "Pressure: " + units.press(ir['AirPressure']), "Density: " + units.dens(ir['AirDensity']), sep=', ')
        print(state.sep_1)
        telem.last_ttemp = ir['TrackTempCrew']
        telem.laps_completed = 0
        telem.laps_remaining = 0
        fuel.used_lap_avg = 0.0
        fuel.used_lap_max = 0.0
        fuel.used_lap_list = []
        state.reset_laps = 0
        fuel.max_pct = DrvInfo("DriverCarMaxFuelPct", 0)
        state.print_sep = True
        telem.session = SessInfo("SessionType")

def TrackTemp():
        PrintSep()
        print("Surface: " + units.temp(ir['TrackTempCrew']))
        print(state.sep_1)
        state.print_sep = True
        telem.last_ttemp = ir['TrackTempCrew']

# iRacing status
def Check_iRacing():
    if state.ir_connected and not (ir.is_initialized and ir.is_connected):
        state.ir_connected = False
        ir.shutdown()
        PrintSep()
        print('iRacing Disconnected')
        print(state.sep_1)
        state.print_sep = True
        telem.session = 0
        fuel.level_full = 0.0
    elif not state.ir_connected and ir.startup() and ir.is_initialized and ir.is_connected:
        state.ir_connected = True
        PrintSep()
        print('iRacing Connected')
        print(state.sep_1)
        state.print_sep = True
        speech_thread = threading.Thread(target=SpeechThread, args=("fuel companion connected",))
        speech_thread.start()

        # Various one-time calls
        units.detect()
        telem.driver_idx = ir['DriverInfo']['DriverCarIdx']
        TrackLength = ir['WeekendInfo']['TrackLength']
        TrackLengthSpl = TrackLength.split()
        telem.lap_distance = float(TrackLengthSpl[0])
        fuel.last_level = ir['FuelLevel']
        fuel.max_pct = DrvInfo("DriverCarMaxFuelPct", 0)
        state.count = ir['LapCompleted'] + 1
        
        fueling_thread = threading.Thread(target=FuelingThread)
        fueling_thread.start()

        # Printing session info
        PrintSep()
        print("Weekend")
        print(state.sep_2)
        print("Track: " + WkndInfo("TrackName", 0), "Car: " + DrvInfo("Drivers", "CarPath"), "Length: " + units.dist(telem.lap_distance, "km"), "Date: " + WkndOpt("Date", 0) + " " + WkndOpt("TimeOfDay", 0) + WkndOpt("TimeOfDay", 1), "Rubber: " + SessInfo("SessionTrackRubberState"), "Max Fuel: " + units.pct(fuel.max_pct), sep=', ')
        state.print_sep = False
        Session()

# Main loop
def Loop():
# Freeze telemetry for consistent data
    ir.freeze_var_buffer_latest() 
    
    # Session type retrieval and change detection
    if state.ir_connected == True:
        SessionType = SessInfo("SessionType")
    else:
        SessionType = telem.session
    if SessionType != telem.session:
        Session()

    telem.flag = str(hex(ir['SessionFlags']))

    if ((ir['TrackTempCrew'] * 1.8) + 32) > ((telem.last_ttemp * 1.8) + 32) + 2 or ((ir['TrackTempCrew'] * 1.8) + 32) < ((telem.last_ttemp * 1.8) + 32) - 2:
        TrackTemp()

    if SessInfo("SessionType") == "Offline Testing" or SessInfo("SessionType") == "Practice":
        if DrvInfo("DriverCarMaxFuelPct", 0) == 1:
            fuel.max_pct = state.practice_fuelpct / 100

        if ir['OilTemp'] == 77.0 and state.reset_laps == 1:
            telem.laps_completed = 0
            fuel.used_lap_avg = 0.0
            fuel.used_lap_max = 0.0
            fuel.used_lap_list = []
            state.reset_laps = 0
        elif ir['OilTemp'] != 77.0:
            state.reset_laps = 1

    # Lap completion trigger
    if ir['LapCompleted'] < state.count:
        state.count = ir['LapCompleted'] + 1
    if ir['LapCompleted'] > state.count + 1:
        state.count = ir['LapCompleted'] + 1
    elif ir['LapCompleted'] == state.count:
        fuel.level = ir['FuelLevel']
        fuel.pct = ir['FuelLevelPct']
        state.count = state.count + 1
        state.trigger = True
    
    # Things to do on lap complete
    if state.trigger == True and fuel.level > 0:
        if SessInfo("SessionType") == "Offline Testing" or SessInfo("SessionType") == "Practice":
            telem.laps_completed = telem.laps_completed + 1
        else:
            telem.laps_completed = ir['LapCompleted']
        if telem.laps_completed <= 0:
            telem.stint_laps = 0
        else:
            telem.stint_laps = telem.stint_laps + 1

        # Estimate laps based on time remaining if session laps aren't set
        if ir['SessionLapsRemain'] > 5000 and ir['LapLastLapTime'] > 1:
            telem.laps_remaining = round(ir['SessionTimeRemain'] / ir['LapLastLapTime'], 0)
        elif ir['SessionLapsRemain'] > 5000 and ir['LapLastLapTime'] < 1:
            telem.laps_remaining = round(ir['SessionTimeRemain'] / (telem.lap_distance / (100 / 3600)), 0)
        elif ir['SessionLapsRemain'] <= 0:
            telem.laps_remaining = 1
        else:
            telem.laps_remaining = ir['SessionLapsRemain'] + 1

        # Use mock race laps for practices
        if SessInfo("SessionType") == "Offline Testing" or SessInfo("SessionType") == "Practice":
            telem.laps_remaining = state.practice_laps - telem.laps_completed

        FuelCalc()

        # Things to do if not under caution or in pit
        if ir['CarIdxPaceLine'][telem.driver_idx] == -1 and ir['CarIdxTrackSurface'][telem.driver_idx] == 3 and ir['SessionState'] == 4 and telem.stint_laps > 1:
            # TTS callouts
            if state.fuel_read == 1 and SessionType != "Lone Qualify":
                speech_thread = threading.Thread(target=SpeechThread, args=(str(round(fuel.laps_left, 2)) + " laps, " + units.vol(fuel.used_lap, "full"),))
                speech_thread.start()

        # Info to print to file/terminal
        ir.unfreeze_var_buffer_latest() 
        time.sleep(1)
        if len(telem.lap_time_list) > 0:
            LapListMax = max(telem.lap_time_list)
        else:
            LapListMax = 999
        if ir['LapLastLapTime'] > 0 and ir['LapLastLapTime'] < (LapListMax + 5):
            telem.lap_time_list.append(ir['LapLastLapTime'])

        LapTime = units.time(ir['LapLastLapTime'])
        if ir['LapLastLapTime'] <= 0.0:
            LapTime = "N/A"

        if telem.laps_completed <= ir['SessionLapsTotal']:
            if SessInfo("SessionType") == "Offline Testing" or SessInfo("SessionType") == "Practice":
                print("Lap ", ir['LapCompleted'], " [Time: ", LapTime, " | Laps: ", round(fuel.laps_left, 2), " | Used: ", units.vol(fuel.used_lap, "abv"), " | Eco: ", units.econ(fuel.eco), "]", sep='')
            else:
                print("Lap ", ir['LapCompleted'], " [Time: ", LapTime, " | Laps: ", round(fuel.laps_left, 2), " | Used: ", units.vol(fuel.used_lap, "abv"), " | Used Rate Req: ", units.vol(fuel.used_lap_req, "abv"), " | Eco: ", units.econ(fuel.eco), " | Eco Req: ", units.econ(fuel.eco_req), " | Level Req: ", units.vol(fuel.level_req, "abv"), "]", sep='')
            state.print_sep = False

        # Lap finishing actions
        fuel.last_level = fuel.level
        state.trigger = False
    elif state.trigger == True and fuel.level <= 0:
        fuel.last_level = fuel.level
        state.trigger = False

    # Pit report

    if ir['CarIdxTrackSurface'][telem.driver_idx] != state.surface and ir['CarIdxTrackSurface'][telem.driver_idx] == 1 or ir['CarIdxTrackSurface'][telem.driver_idx] != state.surface and ir['CarIdxTrackSurface'][telem.driver_idx] == -1:
        fuel.stint_used = fuel.last_pit_level - ir['FuelLevel']
        if fuel.stint_used <= 0:
            fuel.stint_used = fuel.last_pit_level - fuel.last_level
        time.sleep(3)
        if telem.stint_laps > 0:
            PitReport()

    if state.surface == 1 and ir['CarIdxTrackSurface'][telem.driver_idx] != 1:
        fuel.last_pit_level = ir['FuelLevel']
    if state.surface == -1 and ir['CarIdxTrackSurface'][telem.driver_idx] != -1:
        fuel.last_pit_level = ir['FuelLevel']

    state.surface = ir['CarIdxTrackSurface'][telem.driver_idx]

Date = datetime.now()
DateStr = Date.strftime("%Y-%m-%d_%H.%M.%S")

# Write to log file and stdout
if not os.path.exists('logs'):
    os.makedirs('logs')
te = open('logs\\' + DateStr + '.txt', 'w')

class Unbuffered:

   def __init__(self, stream):

       self.stream = stream

   def write(self, data):

       self.stream.write(data)
       self.stream.flush()
       te.write(data)

sys.stdout=Unbuffered(sys.stdout)

def GuiThread():
    sg.theme('LightGray1')

    left_layout = [[sg.Text(text = "Hotkeys:\n\nCtrl+Shift+F1: Print current pace info\nCtrl+Shift+F2: Print fuel to finish info\nCtrl+Shift+F3: Toggle using max fuel usage for auto fueling\nCtrl+Shift+F4: Toggle fuel reading\nCtrl+Shift+F5: Toggle auto fueling\nCtrl+Shift+F6: Set fuel to required")],
                   [sg.Text(text = "Extra laps when auto fueling:"), sg.Spin(values=[i for i in range(0, 26)], initial_value = state.fuel_pad, key = 'FuelPad', enable_events = True)],
                   [sg.Text(text = "Number of laps for race simulation:"), sg.Spin(values=[i for i in range(1, 1000)], initial_value = state.practice_laps, key = 'PracLaps', enable_events = True)],
                   [sg.Text(text = "Max fuel percent for race simulation:"), sg.Spin(values=[i for i in range(1, 101)], initial_value = state.practice_fuelpct, key = 'PracFuelPct', enable_events = True)],
                   [sg.Checkbox('Toggle Fuel Reading', default = state.fuel_read, key = 'FuelRead', enable_events = True), sg.Checkbox('Toggle Auto Fueling', default = state.auto_fuel, key = 'FuelAuto', enable_events = True)],
                   [sg.Checkbox('Use Max Fuel Usage for Auto Fuel', default = state.fuel_max, key = 'FuelMax', enable_events = True)]]

    right_layout = [[sg.Multiline(autoscroll = True, reroute_stdout = True, echo_stdout_stderr = True, enter_submits = False, size = (135, 26), pad = (5,5), font = ('Fixedsys'))]]

    layout = [[sg.Column(left_layout, justification = 'left'), sg.VerticalSeparator(), sg.Column(right_layout)]]

    window = sg.Window('iR Fuel Companion ' + state.version, icon='icon.ico').Layout(layout)

    def CheckUpdate():
        time.sleep(1)
        FuelReadPrev = 0
        AutoFuelPrev = 0
        FuelMaxPrev = 0
        while True:
            if state.fuel_read != FuelReadPrev:
                if state.fuel_read == 1:
                    window['FuelRead'].update(1)
                if state.fuel_read == 0:
                    window['FuelRead'].update(0)
                FuelReadPrev = state.fuel_read

            if state.auto_fuel != AutoFuelPrev:
                if state.auto_fuel == 1:
                    window['FuelAuto'].update(1)
                if state.auto_fuel == 0:
                    window['FuelAuto'].update(0)
                AutoFuelPrev = state.auto_fuel

            if state.fuel_max != FuelMaxPrev:
                if state.fuel_max == 1:
                    window['FuelMax'].update(1)
                if state.fuel_max == 0:
                    window['FuelMax'].update(0)
                FuelMaxPrev = state.fuel_max
            time.sleep(0.1)

    cb_thread = threading.Thread(target=CheckUpdate)
    cb_thread.start()

    while True:
        event, values = window.Read()
        if event == "OK" or event == sg.WIN_CLOSED:
            break

        if event == "FuelRead":
            if values['FuelRead'] == 1:
                state.fuel_read = 1
                SetRegistry()
                #print("Fuel reading enabled")
            else:
                state.fuel_read = 0
                SetRegistry()
                #print("Fuel reading disabled")
        
        if event == "FuelAuto":
            if values['FuelAuto'] == 1:
                state.auto_fuel = 1
                SetRegistry()
                #print("Auto fuel enabled")
            else:
                state.auto_fuel = 0
                SetRegistry()
                #print("Auto fuel disabled")

        if event == "FuelMax":
            if values['FuelMax'] == 1:
                state.fuel_max = 1
                SetRegistry()
                #print("Max fueling enabled")
            else:
                state.fuel_max = 0
                SetRegistry()
                #print("Max fueling disabled")

        if event == "FuelPad":
            state.fuel_pad = values['FuelPad']
            SetRegistry()
        if event == "PracLaps":
            state.practice_laps = values['PracLaps']
            SetRegistry()
        if event == "PracFuelPct":
            state.practice_fuelpct = values['PracFuelPct']
            SetRegistry()
        time.sleep(0.1)
    os._exit(1)
    window.close()

if __name__ == '__main__':
    # Initializing ir and State
    ir = irsdk.IRSDK()
    state = State()
    units = Units()
    fuel = Fuel()
    telem = Telem()
    GetRegistry()
    tts = wincl.Dispatch("SAPI.SpVoice")
    keys_thread = threading.Thread(target=KeysThread)
    keys_thread.start()
    gui_thread = threading.Thread(target=GuiThread)
    gui_thread.start()
    time.sleep(1)
    flags_thread = threading.Thread(target=Flags)
    flags_thread.start()

    print("iR Fuel Companion " + state.version)
    print(state.sep_1)

    try:
        # Check connection and start (or not) loop
        while True:
            Check_iRacing()
            if state.ir_connected:
                Loop()
            te.flush()
            # Data read delay (min 1/60)
            time.sleep(1 / 15)
    except KeyboardInterrupt:
        pass