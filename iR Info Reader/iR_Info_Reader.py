#!python3

import irsdk
import time
import os
import subprocess
import sys
from datetime import datetime

# Write to log file
Date = datetime.now()
DateStr = Date.strftime("%Y-%m-%d_%H.%M.%S")
#sys.stdout = open('output\\' + DateStr + '_log.txt', 'w')

te = open('output\\' + DateStr + '_log.txt', 'w')  # File where you need to keep the logs

class Unbuffered:

   def __init__(self, stream):

       self.stream = stream

   def write(self, data):

       self.stream.write(data)
       self.stream.flush()
       te.write(data)    # Write the data of stdout here to a text file as well



sys.stdout=Unbuffered(sys.stdout)

print("iR Info Reader v0.4")
print("====================")

# Class for storing random variables
class State:
    ir_connected = False
    trigger = False
    last_fuel_level = 0.0
    count = 1
    print_sep = True

# Func to open program
def StartProgram(program):
    #SW_HIDE = 0
    #SW_MINIMIZE = 6
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    #si.wShowWindow = SW_HIDE
    #si.wShowWindow = SW_MINIMIZE
    subprocess.Popen(program, startupinfo=si)

# Func to shorten DriverInfo calls
def DrvInfo(group):
    return ir['DriverInfo']['Drivers'][state.driver_idx][group]

# Func to shorten WeekendInfo calls (and also split string)
def WkndInfo(group, n):
    Result = ir['WeekendInfo'][group]
    ResultSplt = Result.split()
    return ResultSplt[n]

# Func to shorten WeekendOptions calls (and also split string)
def WkndOpt(group, n):
    Result = ir['WeekendInfo']['WeekendOptions'][group]
    ResultSplt = Result.split()
    return ResultSplt[n]

# Func to shorten SessionInfo calls
def SessInfo(group):
    return ir['SessionInfo']['Sessions'][ir['SessionNum']][group]

# Func to return sky status
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

# Func to return a cardinal wind direction
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

def PrintSep():
    if state.print_sep == False:
        print("====================")

# Func to print session info
def Session():
        PrintSep()
        print(SessInfo("SessionType"))
        print("--------------------")
        print("Skies: " + Sky(), "Air: " + str(round((ir['AirTemp'] * 1.8) + 32, 1)) + "f", "Surface: " + str(round((ir['TrackTempCrew'] * 1.8) + 32, 1)) + "f", "Wind: " + WindDir() + " @ " + str(round(ir['WindVel'] * 2.2369362920544025, 1)) + "mph", "Humidity: " + str(round(ir['RelativeHumidity'] * 100, 1)) + "%", "Pressure: " + str(round(ir['AirPressure'], 1)) + "Hg", sep=', ')
        print("====================")
        setattr(State, "print_sep", True)
        setattr(State, "session", SessInfo("SessionType"))

# iRacing status
def check_iracing():
    if state.ir_connected and not (ir.is_initialized and ir.is_connected):
        state.ir_connected = False
        ir.shutdown()
        PrintSep()
        print('iRSDK Disconnected')
        print("====================")
        setattr(State, "print_sep", True)
    elif not state.ir_connected and ir.startup() and ir.is_initialized and ir.is_connected:
        state.ir_connected = True
        PrintSep()
        print('iRSDK Connected')
        print("====================")
        setattr(State, "print_sep", True)

        # Various one-time calls
        setattr(State, "driver_idx", ir['DriverInfo']['DriverCarIdx'])
        TrackLength = ir['WeekendInfo']['TrackLength']
        TrackLengthSpl = TrackLength.split()
        setattr(State, "lap_distance", float(TrackLengthSpl[0]) * 0.621371)
        setattr(State, "last_fuel_level", ir['FuelLevel'] * 0.264172)
        setattr(State, "count", ir['LapCompleted'] + 1)

        # Printing session info
        PrintSep()
        print("Weekend")
        print("--------------------")
        print("Track: " + WkndInfo("TrackName", 0), "Car: " + DrvInfo("CarPath"), "Length: " + str(round(state.lap_distance, 2)) + "mi", "Date: " + WkndOpt("Date", 0) + " " + WkndOpt("TimeOfDay", 0) + WkndOpt("TimeOfDay", 1), "Rubber: " + SessInfo("SessionTrackRubberState"), sep=', ')
        setattr(State, "print_sep", False)
        Session()

# Main loop
def loop():
    # l * 0.264172 = l to gal | km * 0.621371 = km to mi | m * 0.000621371 = m to mi | (c * 1.8) + 32 = c to f | mph / 1.609344 = kph to mph | rad * 57.295779513 = rad to deg | m/s to mph = m/s * 2.2369362920544025

    # Freeze telemetry for consistent data
    ir.freeze_var_buffer_latest()
    
    # Session type retrieval and change detection
    SessionType = SessInfo("SessionType")
    if SessionType != state.session:
        Session()

    # Lap completion trigger
    if ir['LapCompleted'] < state.count:
        setattr(State, "count", ir['LapCompleted'] + 1)
    if ir['LapCompleted'] > state.count + 1:
        setattr(State, "count", ir['LapCompleted'] + 1)
    elif ir['LapCompleted'] == state.count:
        setattr(State, "fuel_level", ir['FuelLevel'] * 0.264172)
        setattr(State, "count", state.count + 1)
        setattr(State, "trigger", True)
    
    # Things to do on lap complete
    if state.trigger == True and state.fuel_level > 0:
        LapsCompleted = ir['LapCompleted']

        # Use time estimates if session is timed
        if ir['SessionLapsRemain'] > 5000 and ir['LapLastLapTime'] > 1:
            LapsRemain = round(ir['SessionTimeRemain'] / ir['LapLastLapTime'], 0)
        elif ir['SessionLapsRemain'] <= 0:
            LapsRemain = 1
        else:
            LapsRemain = ir['SessionLapsRemain'] + 1

        # Fuel variables and calc
        FuelUsed = state.last_fuel_level - state.fuel_level
        FuelUsedReq = state.fuel_level / LapsRemain
        if FuelUsed > 0:
            FuelLaps = state.fuel_level / FuelUsed
            FuelMPG = state.lap_distance / FuelUsed
        else:
            FuelLaps = 0
            FuelMPG = 0
        FuelMPGReq = (state.lap_distance * LapsRemain) / state.fuel_level
        FuelLevelReq = (LapsRemain * FuelUsed) - state.fuel_level
        # Info to print to file/terminal
        if LapsCompleted <= ir['SessionLapsTotal']:
            print("Lap ", LapsCompleted, " Report [Laps: ", round(FuelLaps, 2), " | Used: ", round(FuelUsed, 3), "gal | Used Rate Req: ", round(FuelUsedReq, 3), "gal | MPG: ", round(FuelMPG, 2), "mpg | MPG Req: ", round(FuelMPGReq, 2), "mpg | Total: ", round(FuelLevelReq, 3), "gal]", sep='')
            setattr(State, "print_sep", False)
        # Send info to VoiceAttack and trigger commands    
        StartProgram('cmd /c "C:\Program Files (x86)\VoiceAttack\VoiceAttack.exe" -Command external_variables -PassedDecimal ' +(str(round(FuelLaps, 2)))+ ";" +(str(round(FuelUsed, 3)))+ ";" +(str(round(FuelUsedReq, 3)))+ ";" +(str(round(FuelMPG, 2)))+ ";" +(str(round(FuelMPGReq, 2)))+ ";" +(str(round(FuelLevelReq, 3))))
        time.sleep(0.1)
        if ir['CarIdxPaceLine'][state.driver_idx] == -1 and ir['CarIdxTrackSurface'][state.driver_idx] == 3 and SessionType != "Lone Qualify" and ir['SessionState'] == 4 and FuelUsed > 0:
            StartProgram('cmd /c "C:\Program Files (x86)\VoiceAttack\VoiceAttack.exe" -Command fuel_read')

        # Lap finishing actions
        setattr(State, "last_fuel_level", state.fuel_level)
        setattr(State, "trigger", False)
    elif state.trigger == True and state.fuel_level <= 0:
        setattr(State, "last_fuel_level", state.fuel_level)
        setattr(State, "trigger", False)

if __name__ == '__main__':
    # Initializing ir and State
    ir = irsdk.IRSDK()
    state = State()
    
    try:
        # Check connection and start (or not) loop
        while True:
            check_iracing()
            if state.ir_connected:
                loop()
            te.flush()
            # Data read delay (min 1/60)
            time.sleep(1 / 15)
    except KeyboardInterrupt:
        pass