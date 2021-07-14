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
    version = "v0.0.3"
    reg_path = 'Software\\iR Fuel Companion'
    ir_connected = False
    trigger = False
    count = 1
    print_sep = True
    fuel_read = 1
    auto_fuel = 1
    fuel_pad = 2

# Fuel variables
class Fuel:
    level = 0.0
    last_level = 0.0
    used_lap = 0.0
    used_lap_req = 0.0
    laps_left = 0.0
    mpg = 0.0
    mpg_req = 0.0
    level_req = 0.0
    level_req_avg = 0.0

# Other iR telemetry variables
class Telem:
    laps_completed = 0
    laps_remaining = 0
    lap_distance = 0
    driver_idx = 0
    session = 0
    location = 1

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
        setattr(State, "fuel_read", str(reg.get_reg(state.reg_path, 'Read')))
    if reg.get_reg(state.reg_path, 'Auto'):
        setattr(State, "auto_fuel", str(reg.get_reg(state.reg_path, 'Auto')))
    if reg.get_reg(state.reg_path, 'Pad'):
        setattr(State, "fuel_pad", int(reg.get_reg(state.reg_path, 'Pad')))
    SetRegistry()

def SetRegistry():
    reg.set_reg(state.reg_path, 'Read', str(state.fuel_read))
    reg.set_reg(state.reg_path, 'Auto', str(state.auto_fuel))
    reg.set_reg(state.reg_path, 'Pad', str(state.fuel_pad))

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
            keyboard.write("## Current pace - " + str(round(getattr(Fuel, "laps_left"), 2)) + " laps, " + str(round(getattr(Fuel, "level_req_avg"), 3)) + " gal extra ##")
            time.sleep(0.05)
            keyboard.send('enter')
            time.sleep(0.05)
            ir.chat_command(3)
            time.sleep(0.75)
        if keyboard.is_pressed('ctrl+shift+f2') == True:
            time.sleep(0.25)
            ir.chat_command(1)
            time.sleep(0.05)
            keyboard.write("## Last lap - " + str(round(getattr(Fuel, "used_lap"), 3)) + " gal, " + str(round(getattr(Fuel, "mpg"), 2)) + " mpg ##")
            time.sleep(0.05)
            keyboard.send('enter')
            time.sleep(0.05)
            ir.chat_command(3)
            time.sleep(0.75)
        if keyboard.is_pressed('ctrl+shift+f3') == True:
            time.sleep(0.25)
            ir.chat_command(1)
            time.sleep(0.05)
            keyboard.write("## To finish - " + str(round(getattr(Fuel, "used_lap_req"), 3)) + " gal, " + str(round(getattr(Fuel, "mpg_req"), 2)) + " mpg ##")
            time.sleep(0.05)
            keyboard.send('enter')
            time.sleep(0.05)
            ir.chat_command(3)
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
        if keyboard.is_pressed('1') == 1:
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
        setattr(Fuel, "used_lap", fuel.last_level - fuel.level)
        if telem.laps_remaining > 0:
            setattr(Fuel, "used_lap_req", fuel.level / telem.laps_remaining)
        else:
            setattr(Fuel, "used_lap_req", 0.000)
        if fuel.used_lap > 0:
            setattr(Fuel, "laps_left", fuel.level / fuel.used_lap)
            setattr(Fuel, "mpg", telem.lap_distance / fuel.used_lap)
        elif fuel.used_lap < 0:
            setattr(Fuel, "laps_left", 0.00)
            setattr(Fuel, "mpg", 0.00)
        else:
            setattr(Fuel, "laps_left", 999.00)
            setattr(Fuel, "mpg", 99.00)
        setattr(Fuel, "mpg_req", (telem.lap_distance * telem.laps_remaining) / fuel.level)
        setattr(Fuel, "level_req", ((telem.laps_remaining + state.fuel_pad) * fuel.used_lap) - fuel.level)

def FuelingThread():
    Pitting = True
    PittingChgd = True
    while True:
        while SessInfo("SessionType") == "Race" and state.auto_fuel == 1 and state.ir_connected == True:
            FuelLevelReqL = fuel.level_req_avg * 3.785411784
            FuelLastLevelL = fuel.last_level * 3.785411784
            if Pitting == True and PittingChgd == True:
                if FuelLevelReqL + FuelLastLevelL <= ir['FuelLevel']:
                    ir.pit_command(11)
                if FuelLevelReqL + FuelLastLevelL > ir['FuelLevel']:
                    ir.pit_command(2, int(round(FuelLevelReqL, 0)))
                    while ir['CarIdxTrackSurface'][telem.driver_idx] == 1:
                        if FuelLevelReqL + FuelLastLevelL <= ir['FuelLevel']:
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

# Return a cardinal wind direction
def WindDir():
    WindDeg = ir['WindDir'] * 57.295779513
    WindCard = "N/A"
    if WindDeg >= 337.5 or WindDeg <= 22.5:
        WindCard = "N"
    elif WindDeg > 22.5 and WindDeg < 67.5:
        WindCard = "NE"
    elif WindDeg >= 67.5 and WindDeg <= 112.5:
        WindCard = "E"
    elif WindDeg > 112.5 and WindDeg < 157.5:
        WindCard = "SE"
    elif WindDeg >= 157.5 and WindDeg <= 202.5:
        WindCard = "S"
    elif WindDeg > 202.5 and WindDeg < 247.5:
        WindCard = "SW"
    elif WindDeg >= 247.5 and WindDeg <= 292.5:
        WindCard = "W"
    elif WindDeg > 292.5 and WindDeg < 337.5:
        WindCard = "NW"
    return WindCard

# Func to not double up on seperators because it bothered me
def PrintSep():
    if state.print_sep == False:
        print("==================================================================================================================================")

# Print session info
def Session():
        PrintSep()
        print(SessInfo("SessionType"))
        print("----------------------------------------------------------------------------------------------------------------------------------")
        print("Skies: " + Sky(), "Air: " + str(round((ir['AirTemp'] * 1.8) + 32, 1)) + "f", "Surface: " + str(round((ir['TrackTempCrew'] * 1.8) + 32, 1)) + "f", "Wind: " + WindDir() + " @ " + str(round(ir['WindVel'] * 2.2369362920544025, 1)) + "mph", "Humidity: " + str(round(ir['RelativeHumidity'] * 100, 1)) + "%", "Pressure: " + str(round(ir['AirPressure'], 1)) + "Hg", sep=', ')
        print("==================================================================================================================================")
        setattr(State, "print_sep", True)
        setattr(Telem, "session", SessInfo("SessionType"))

# iRacing status
def Check_iRacing():
    if state.ir_connected and not (ir.is_initialized and ir.is_connected):
        state.ir_connected = False
        ir.shutdown()
        PrintSep()
        print('iRSDK Disconnected')
        print("==================================================================================================================================")
        setattr(State, "print_sep", True)
        setattr(Telem, "session", 0)
    elif not state.ir_connected and ir.startup() and ir.is_initialized and ir.is_connected:
        state.ir_connected = True
        PrintSep()
        print('iRSDK Connected')
        print("==================================================================================================================================")
        setattr(State, "print_sep", True)
        speech_thread = threading.Thread(target=SpeechThread, args=("fuel companion connected",))
        speech_thread.start()

        # Various one-time calls
        global last_level_req_list
        setattr(Telem, "driver_idx", ir['DriverInfo']['DriverCarIdx'])
        TrackLength = ir['WeekendInfo']['TrackLength']
        TrackLengthSpl = TrackLength.split()
        setattr(Telem, "lap_distance", float(TrackLengthSpl[0]) * 0.621371)
        setattr(Fuel, "last_level", ir['FuelLevel'] * 0.264172)
        setattr(State, "count", ir['LapCompleted'] + 1)
        last_level_req_list = []
        fueling_thread = threading.Thread(target=FuelingThread)
        fueling_thread.start()

        # Printing session info
        PrintSep()
        print("Weekend")
        print("----------------------------------------------------------------------------------------------------------------------------------")
        print("Track: " + WkndInfo("TrackName", 0), "Car: " + DrvInfo("CarPath"), "Length: " + str(round(telem.lap_distance, 2)) + "mi", "Date: " + WkndOpt("Date", 0) + " " + WkndOpt("TimeOfDay", 0) + WkndOpt("TimeOfDay", 1), "Rubber: " + SessInfo("SessionTrackRubberState"), sep=', ')
        setattr(State, "print_sep", False)
        Session()

# Main loop
def Loop():
    # l * 0.264172 = l to gal | km * 0.621371 = km to mi | m * 0.000621371 = m to mi | (c * 1.8) + 32 = c to f | mph / 1.609344 = kph to mph | rad * 57.295779513 = rad to deg | m/s to mph = m/s * 2.2369362920544025

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
        setattr(Fuel, "level", ir['FuelLevel'] * 0.264172)
        setattr(State, "count", state.count + 1)
        setattr(State, "trigger", True)
    
    # Things to do on lap complete
    if state.trigger == True and fuel.level > 0:
        global last_level_req_list
        setattr(Telem, "laps_completed", ir['LapCompleted'])

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
        if ir['CarIdxPaceLine'][telem.driver_idx] == -1 and ir['CarIdxTrackSurface'][telem.driver_idx] == 3 and ir['SessionState'] == 4 and fuel.used_lap > 0:
            if len(last_level_req_list) >= 5:
                last_level_req_list.pop(0)
            last_level_req_list.append(fuel.level_req)
            if len(last_level_req_list) > 0:
                total = 0
                for level in last_level_req_list:
                    total = total + level
                setattr(Fuel, "level_req_avg", total / len(last_level_req_list))
            # TTS callouts
            if state.fuel_read == 1 and SessionType != "Lone Qualify":
                speech_thread = threading.Thread(target=SpeechThread, args=(str(round(fuel.laps_left, 2)) + " laps, " + str(round(fuel.used_lap, 3)) + " gallons",))
                speech_thread.start()

        # Info to print to file/terminal
        if telem.laps_completed <= ir['SessionLapsTotal']:
            print("Lap ", telem.laps_completed, " Report [Laps: ", round(fuel.laps_left, 2), " | Used: ", round(fuel.used_lap, 3), "gal | Used Rate Req: ", round(fuel.used_lap_req, 3), "gal | MPG: ", round(fuel.mpg, 2), "mpg | MPG Req: ", round(fuel.mpg_req, 2), "mpg | Total: ", round(fuel.level_req_avg, 3), "gal]", sep='')
            setattr(State, "print_sep", False)

        # Send info to VoiceAttack and trigger commands    
        #StartProgram('cmd /c "C:\Program Files (x86)\VoiceAttack\VoiceAttack.exe" -Command external_variables -PassedDecimal ' +(str(round(FuelLaps, 2)))+ ";" +(str(round(FuelUsed, 3)))+ ";" +(str(round(FuelUsedReq, 3)))+ ";" +(str(round(FuelMPG, 2)))+ ";" +(str(round(FuelMPGReq, 2)))+ ";" +(str(round(FuelLevelReq, 3))))
        #time.sleep(0.1)
        #StartProgram('cmd /c "C:\Program Files (x86)\VoiceAttack\VoiceAttack.exe" -Command fuel_read')

        # Lap finishing actions
        setattr(Fuel, "last_level", fuel.level)
        setattr(State, "trigger", False)
    elif state.trigger == True and fuel.level <= 0:
        setattr(Fuel, "last_level", fuel.level)
        setattr(State, "trigger", False)

Date = datetime.now()
DateStr = Date.strftime("%Y-%m-%d_%H.%M.%S")

# Write to log file and stdout
if not os.path.exists('logs'):
    os.makedirs('logs')
te = open('logs\\' + DateStr + '.txt', 'w')  # File where you need to keep the logs

class Unbuffered:

   def __init__(self, stream):

       self.stream = stream

   def write(self, data):

       self.stream.write(data)
       self.stream.flush()
       te.write(data)    # Write the data of stdout here to a text file as well

sys.stdout=Unbuffered(sys.stdout)

def GuiThread():
    sg.theme('LightGray1')  # please make your windows colorful

    left_layout = [[sg.Text(text = "Hotkeys:\n\nCtrl+Shift+F1: Print current pace info\nCtrl+Shift+F2: Print last lap info\nCtrl+Shift+F3: Print fuel to finish info\nCtrl+Shift+F4: Toggle fuel reading\nCtrl+Shift+F5: Toggle auto fueling")],
                   [sg.Text(text = "Extra laps when auto fueling:"), sg.Spin(values=[i for i in range(0, 26)], initial_value = state.fuel_pad, key = 'FuelPad', enable_events = True)],
                   [sg.Checkbox('Toggle Fuel Reading', default = state.fuel_read, key = 'FuelRead', enable_events = True), sg.Checkbox('Toggle Auto Fueling', default = state.auto_fuel, key = 'FuelAuto', enable_events = True)]]#,
                   #[sg.Button("Current Pace"), sg.Button("Last Lap"), sg.Button("To Finish")]]

    right_layout = [[sg.Multiline(autoscroll = True, reroute_stdout = True, echo_stdout_stderr = True, enter_submits = False, size = (130, 26), pad = (5,5), font = ('Fixedsys'))]]

    layout = [[sg.Column(left_layout, justification = 'left'), sg.VerticalSeparator(), sg.Column(right_layout)]]

    window = sg.Window('iR Fuel Companion ' + state.version, icon='icon.ico').Layout(layout)

    def CheckUpdate():
        time.sleep(1)
        FuelReadPrev = 0
        AutoFuelPrev = 0
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
    print("==================================================================================================================================")

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