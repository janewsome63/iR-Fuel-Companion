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
from datetime import datetime

# Random variables
class State:
    version = "v0.0.8"
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
    last_level = 0.0
    used_lap = 0.0
    used_lap_req = 0.0
    laps_left = 0.0
    eco = 0.0
    eco_req = 0.0
    level_req = 0.0
    level_req_max = 0.0
    level_req_avg = 0.0
    last_level_req_list = []
    stint_used = 0.0
    stint_used_avg = 0.0
    stint_eco = 0.0
    last_pit_level = 0.0

# Other iR telemetry variables
class Telem:
    laps_completed = 0
    laps_remaining = 0
    lap_distance = 0
    driver_idx = 0
    session = 0
    location = 1
    stint_laps = 0

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
        setattr(State, "fuel_read", reg.get_reg(state.reg_path, 'Read'))
    if reg.get_reg(state.reg_path, 'Auto'):
        setattr(State, "auto_fuel", reg.get_reg(state.reg_path, 'Auto'))
    if reg.get_reg(state.reg_path, 'Max'):
        setattr(State, "fuel_max", reg.get_reg(state.reg_path, 'Max'))
    if reg.get_reg(state.reg_path, 'Pad'):
        setattr(State, "fuel_pad", reg.get_reg(state.reg_path, 'Pad'))
    SetRegistry()

def SetRegistry():
    reg.set_reg(state.reg_path, 'Read', state.fuel_read)
    reg.set_reg(state.reg_path, 'Auto', state.auto_fuel)
    reg.set_reg(state.reg_path, 'Max', state.fuel_max)
    reg.set_reg(state.reg_path, 'Pad', state.fuel_pad)

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
            keyboard.write("## Current pace - " + str(round(fuel.laps_left, 2)) + " laps, " + units.vol(fuel.used_lap, "abv") + ", " + units.econ(fuel.eco) + " ##")
            time.sleep(0.05)
            keyboard.send('enter')
            time.sleep(0.05)
            ir.chat_command(3)
            time.sleep(0.75)
        if keyboard.is_pressed('ctrl+shift+f2') == True:
            time.sleep(0.25)
            ir.chat_command(1)
            time.sleep(0.05)
            keyboard.write("## To finish - " + units.vol(fuel.used_lap_req, "abv") + ", " + units.econ(fuel.eco_req) + ", " + units.vol(fuel.level_req_avg, "abv") + " extra ##")
            time.sleep(0.05)
            keyboard.send('enter')
            time.sleep(0.05)
            ir.chat_command(3)
            time.sleep(0.75)
        if keyboard.is_pressed('ctrl+shift+f3') == True:
            time.sleep(0.25)
            if state.fuel_max == 1:
                setattr(State, "fuel_max", 0)
                SetRegistry()
                speech_thread = threading.Thread(target=SpeechThread, args=("using average fuel usage for auto fuel",))
                speech_thread.start()
            elif state.fuel_max == 0:
                setattr(State, "fuel_max", 1)
                SetRegistry()
                speech_thread = threading.Thread(target=SpeechThread, args=("using max fuel usage for auto fuel",))
                speech_thread.start()
            time.sleep(0.75)
        if keyboard.is_pressed('ctrl+shift+f4') == True:
            time.sleep(0.25)
            if state.fuel_read == 1:
                setattr(State, "fuel_read", 0)
                SetRegistry()
                speech_thread = threading.Thread(target=SpeechThread, args=("fuel reading disabled",))
                speech_thread.start()
            elif state.fuel_read == 0:
                setattr(State, "fuel_read", 1)
                SetRegistry()
                speech_thread = threading.Thread(target=SpeechThread, args=("fuel reading enabled",))
                speech_thread.start()
            time.sleep(0.75)
        if keyboard.is_pressed('ctrl+shift+f5') == True:
            time.sleep(0.25)
            if state.auto_fuel == 1:
                setattr(State, "auto_fuel", 0)
                SetRegistry()
                speech_thread = threading.Thread(target=SpeechThread, args=("auto fuel disabled",))
                speech_thread.start()
            elif state.auto_fuel == 0:
                setattr(State, "auto_fuel", 1)
                SetRegistry()
                speech_thread = threading.Thread(target=SpeechThread, args=("auto fuel enabled",))
                speech_thread.start()
            time.sleep(0.75)
        time.sleep(1/60)

# Fuel calculations
def FuelCalc():
        if telem.laps_remaining > 0:
            setattr(Fuel, "used_lap_req", fuel.level / telem.laps_remaining)
        else:
            setattr(Fuel, "used_lap_req", 0.000)
        setattr(Fuel, "used_lap", fuel.last_level - fuel.level)
        if fuel.used_lap < 0:
            setattr(Fuel, "used_lap", fuel.last_pit_level - fuel.level)
        if fuel.used_lap > 0:
            setattr(Fuel, "laps_left", fuel.level / fuel.used_lap)
            setattr(Fuel, "eco", telem.lap_distance / fuel.used_lap)
        else:
            setattr(Fuel, "laps_left", 999.00)
            setattr(Fuel, "eco", 99.00)
        setattr(Fuel, "eco_req", (telem.lap_distance * telem.laps_remaining) / fuel.level)
        setattr(Fuel, "level_req", (((telem.laps_remaining + state.fuel_pad) * fuel.used_lap) - fuel.level))

def FuelingThread():
    Pitting = True
    PittingChgd = True
    while True:
        while SessInfo("SessionType") == "Race" and state.auto_fuel == 1 and state.ir_connected == True:
            if Pitting == True and PittingChgd == True:
                FuelAdd = fuel.level_req_avg
                if state.fuel_max == 1:
                    FuelAdd = fuel.level_req_max
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
            time.sleep(1/60)
        time.sleep(1/5)

def PitReport():
    fuel.stint_used_avg = fuel.stint_used / telem.stint_laps
    fuel.stint_eco = (telem.stint_laps * telem.lap_distance) / fuel.stint_used
    ir.unfreeze_var_buffer_latest()
    PrintSep()
    print("Lap", telem.laps_completed + 1, "Pit Report")
    print(state.sep_2)
    print("Stint: " + str(telem.stint_laps) + " laps", "Avg Used: " + units.vol(fuel.stint_used_avg, "abv"), "Avg Eco: " + units.econ(fuel.stint_eco), "Total Used: " + units.vol(fuel.stint_used, "abv"), sep=', ')
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
    setattr(State, "print_sep", True)
    fuel.level_req_max = 0.0
    fuel.last_level_req_list.clear()
    telem.stint_laps = 0
    fuel.stint_used = 0.0

# Shorten DriverInfo calls
def DrvInfo(group):
    return ir['DriverInfo']['Drivers'][telem.driver_idx][group]

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
        PrintSep()
        print(SessInfo("SessionType"))
        print(state.sep_2)
        print("Skies: " + Sky(), "Air: " + units.temp(ir['AirTemp']), "Surface: " + units.temp(ir['TrackTempCrew']), "Wind: " + units.wind_dir() + " @ " + units.speed(ir['WindVel']), "Humidity: " + units.pct(ir['RelativeHumidity']), "Pressure: " + units.press(ir['AirPressure']), "Density: " + units.dens(ir['AirDensity']), sep=', ')
        print(state.sep_1)
        setattr(State, "print_sep", True)
        setattr(Telem, "session", SessInfo("SessionType"))

# iRacing status
def Check_iRacing():
    if state.ir_connected and not (ir.is_initialized and ir.is_connected):
        state.ir_connected = False
        ir.shutdown()
        PrintSep()
        print('iRacing Disconnected')
        print(state.sep_1)
        setattr(State, "print_sep", True)
        setattr(Telem, "session", 0)
    elif not state.ir_connected and ir.startup() and ir.is_initialized and ir.is_connected:
        state.ir_connected = True
        PrintSep()
        print('iRacing Connected')
        print(state.sep_1)
        setattr(State, "print_sep", True)
        speech_thread = threading.Thread(target=SpeechThread, args=("fuel companion connected",))
        speech_thread.start()

        # Various one-time calls
        units.detect()
        setattr(Telem, "driver_idx", ir['DriverInfo']['DriverCarIdx'])
        TrackLength = ir['WeekendInfo']['TrackLength']
        TrackLengthSpl = TrackLength.split()
        setattr(Telem, "lap_distance", float(TrackLengthSpl[0]))
        setattr(Fuel, "last_level", ir['FuelLevel'])
        setattr(State, "count", ir['LapCompleted'] + 1)
        
        fueling_thread = threading.Thread(target=FuelingThread)
        fueling_thread.start()

        # Printing session info
        PrintSep()
        print("Weekend")
        print(state.sep_2)
        print("Track: " + WkndInfo("TrackName", 0), "Car: " + DrvInfo("CarPath"), "Length: " + units.dist(telem.lap_distance, "km"), "Date: " + WkndOpt("Date", 0) + " " + WkndOpt("TimeOfDay", 0) + WkndOpt("TimeOfDay", 1), "Rubber: " + SessInfo("SessionTrackRubberState"), sep=', ')
        setattr(State, "print_sep", False)
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

    # Lap completion trigger
    if ir['LapCompleted'] < state.count:
        setattr(State, "count", ir['LapCompleted'] + 1)
    if ir['LapCompleted'] > state.count + 1:
        setattr(State, "count", ir['LapCompleted'] + 1)
    elif ir['LapCompleted'] == state.count:
        setattr(Fuel, "level", ir['FuelLevel'])
        setattr(State, "count", state.count + 1)
        setattr(State, "trigger", True)
    
    # Things to do on lap complete
    if state.trigger == True and fuel.level > 0:
        setattr(Telem, "laps_completed", ir['LapCompleted'])
        telem.stint_laps = telem.stint_laps + 1

        # Use time estimates if session is timed
        if ir['SessionLapsRemain'] > 5000 and ir['LapLastLapTime'] > 1:
            setattr(Telem, "laps_remaining", round(ir['SessionTimeRemain'] / ir['LapLastLapTime'], 0))
        elif ir['SessionLapsRemain'] > 5000 and ir['LapLastLapTime'] < 1:
            setattr(Telem, "laps_remaining", round(ir['SessionTimeRemain'] / (telem.lap_distance / (100 / 3600)), 0))
        elif ir['SessionLapsRemain'] <= 0:
            setattr(Telem, "laps_remaining", 1)
        else:
            setattr(Telem, "laps_remaining", ir['SessionLapsRemain'] + 1)

        FuelCalc()

        # Things to do if not under caution or in pit
        if ir['CarIdxPaceLine'][telem.driver_idx] == -1 and ir['CarIdxTrackSurface'][telem.driver_idx] == 3 and ir['SessionState'] == 4 and telem.stint_laps > 1:
            if fuel.level_req + 2 > fuel.level_req_max:
                fuel.level_req_max = fuel.level_req + 2 # 2 extra liters added for safety
            if len(fuel.last_level_req_list) >= 5:
                fuel.last_level_req_list.pop(0)
            fuel.last_level_req_list.append(fuel.level_req)
            if len(fuel.last_level_req_list) > 0:
                total = 0
                for level in fuel.last_level_req_list:
                    total = total + level
                setattr(Fuel, "level_req_avg", (total / len(fuel.last_level_req_list)) + 2) # 2 extra liters added for safety
            # TTS callouts
            if state.fuel_read == 1 and SessionType != "Lone Qualify":
                speech_thread = threading.Thread(target=SpeechThread, args=(str(round(fuel.laps_left, 2)) + " laps, " + units.vol(fuel.used_lap, "full"),))
                speech_thread.start()

        # Info to print to file/terminal
        if telem.laps_completed <= ir['SessionLapsTotal']:
            if SessInfo("SessionType") == "Offline Testing" or SessInfo("SessionType") == "Practice":
                print("Lap ", telem.laps_completed, " [Laps: ", round(fuel.laps_left, 2), " | Used: ", units.vol(fuel.used_lap, "abv"), " | Eco: ", units.econ(fuel.eco), "]", sep='')
            else:
                print("Lap ", telem.laps_completed, " [Laps: ", round(fuel.laps_left, 2), " | Used: ", units.vol(fuel.used_lap, "abv"), " | Used Rate Req: ", units.vol(fuel.used_lap_req, "abv"), " | Eco: ", units.econ(fuel.eco), " | Eco Req: ", units.econ(fuel.eco_req), " | Total: ", units.vol(fuel.level_req_avg, "abv"), "]", sep='')
            setattr(State, "print_sep", False)

        # Lap finishing actions
        setattr(Fuel, "last_level", fuel.level)
        setattr(State, "trigger", False)
    elif state.trigger == True and fuel.level <= 0:
        setattr(Fuel, "last_level", fuel.level)
        setattr(State, "trigger", False)

    # Pit report
    if ir['CarIdxTrackSurface'][telem.driver_idx] != state.surface and ir['CarIdxTrackSurface'][telem.driver_idx] == 1 or ir['CarIdxTrackSurface'][telem.driver_idx] != state.surface and ir['CarIdxTrackSurface'][telem.driver_idx] == -1:
        fuel.stint_used = fuel.last_pit_level - ir['FuelLevel']
        if fuel.stint_used < 0:
            fuel.stint_used = fuel.last_pit_level - fuel.last_level
        time.sleep(3)
        if telem.stint_laps > 0:
            PitReport()

    if state.surface == 1 and ir['CarIdxTrackSurface'][telem.driver_idx] != 1:
        fuel.last_pit_level = ir['FuelLevel']
    if state.surface == -1 and ir['CarIdxTrackSurface'][telem.driver_idx] != -1:
        fuel.last_pit_level = ir['FuelLevel']

    setattr(State, "surface", ir['CarIdxTrackSurface'][telem.driver_idx])

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

    left_layout = [[sg.Text(text = "Hotkeys:\n\nCtrl+Shift+F1: Print current pace info\nCtrl+Shift+F2: Print fuel to finish info\nCtrl+Shift+F3: Toggle using max fuel usage for auto fueling\nCtrl+Shift+F4: Toggle fuel reading\nCtrl+Shift+F5: Toggle auto fueling")],
                   [sg.Text(text = "Extra laps when auto fueling:"), sg.Spin(values=[i for i in range(0, 26)], initial_value = state.fuel_pad, key = 'FuelPad', enable_events = True)],
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
                setattr(State, "fuel_read", 1)
                SetRegistry()
                #print("Fuel reading enabled")
            else:
                setattr(State, "fuel_read", 0)
                SetRegistry()
                #print("Fuel reading disabled")
        
        if event == "FuelAuto":
            if values['FuelAuto'] == 1:
                setattr(State, "auto_fuel", 1)
                SetRegistry()
                #print("Auto fuel enabled")
            else:
                setattr(State, "auto_fuel", 0)
                SetRegistry()
                #print("Auto fuel disabled")

        if event == "FuelMax":
            if values['FuelMax'] == 1:
                setattr(State, "fuel_max", 1)
                SetRegistry()
                #print("Max fueling enabled")
            else:
                setattr(State, "fuel_max", 0)
                SetRegistry()
                #print("Max fueling disabled")

        if event == "FuelPad":
            setattr(State, "fuel_pad", values['FuelPad'])
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