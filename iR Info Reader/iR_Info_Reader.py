#!python3

import irsdk
import time
import os
import subprocess
import sys

output = open('output\\log.txt', 'w')

print("iR Info Reader v0.3", file = output)
print("====================", file = output)

class State:
    ir_connected = False
    trigger = False
    last_fuel_level = 0.0
    count = 1

def DrvInfo(group):
    return ir['DriverInfo']['Drivers'][state.driver_idx][group]

def WkndInfo(group, n):
    Result = ir['WeekendInfo'][group]
    ResultSplt = Result.split()
    return ResultSplt[n]

def WkndOpt(group, n):
    Result = ir['WeekendInfo']['WeekendOptions'][group]
    ResultSplt = Result.split()
    return ResultSplt[n]

def SessInfo(group):
    return ir['SessionInfo']['Sessions'][ir['SessionNum']][group]

# iRacing status
def check_iracing():
    if state.ir_connected and not (ir.is_initialized and ir.is_connected):
        state.ir_connected = False
        ir.shutdown()
        print("====================", file = output)
        print('iRSDK Disconnected', file = output)
        print("====================", file = output)
    elif not state.ir_connected and ir.startup() and ir.is_initialized and ir.is_connected:
        state.ir_connected = True
        print('iRSDK Connected', file = output)
        print("====================", file = output)
        setattr(State, "driver_idx", ir['DriverInfo']['DriverCarIdx'])
        TrackLength = ir['WeekendInfo']['TrackLength']
        TrackLengthSpl = TrackLength.split()
        setattr(State, "lap_distance", float(TrackLengthSpl[0]) * 0.621371)
        setattr(State, "last_fuel_level", ir['FuelLevel'] * 0.264172)
        setattr(State, "count", ir['Lap'] + 1)
        print("Track: " + WkndInfo("TrackName", 0), "Car: " + DrvInfo("CarPath"), "Length: " + str(round(state.lap_distance, 2)) + "mi", "Date: " + WkndOpt("Date", 0) + " " + WkndOpt("TimeOfDay", 0) + WkndOpt("TimeOfDay", 1), "Rubber: " + SessInfo("SessionTrackRubberState"), sep=', ', file = output)
        print("Skies: " + ir['WeekendInfo']['WeekendOptions']['Skies'], "Surface: " + str(round((ir['AirTemp'] * 1.8) + 32, 1)) + "f", "Track: " + str(round((ir['TrackTempCrew'] * 1.8) + 32, 1)) + "f", "Wind: " + WkndOpt("WindDirection", 0) + " @ " + str(round(float(WkndOpt("WindSpeed", 0)) / 1.609344, 1)) + "mph", "Humidity: " + str(round(ir['RelativeHumidity'] * 100, 1)) + "%", "Pressure: " + str(round(ir['AirPressure'], 1)) + "Hg", sep=', ', file = output)
        print("====================", file = output)
        print(SessInfo("SessionType"), file = output)
        print("====================", file = output)
        setattr(State, "session", SessInfo("SessionType"))

# Main loop
def loop():
    # 0.264172 = l to gal, 0.621371 = km to mi, 0.000621371 = m to mi, c to f = (0°C × 1.8) + 32

    # Freeze telemetry for consistent data
    ir.freeze_var_buffer_latest()
    
    # General retrievals
    SessionType = SessInfo("SessionType")
    if SessionType != state.session:
        print("====================", file = output)
        print(SessInfo("SessionType"), file = output)
        print("====================", file = output)
        setattr(State, "session", SessInfo("SessionType"))
    # Lap completion trigger, etc
    if ir['Lap'] < state.count - 1:
        setattr(State, "count", ir['Lap'] + 1)
    elif ir['Lap'] == state.count:
        setattr(State, "fuel_level", ir['FuelLevel'] * 0.264172)
        setattr(State, "count", ir['Lap'] + 1)
        state.trigger = True
    
    # Things to do on lap complete
    if state.trigger == True:
        LapsCompleted = ir['LapCompleted']
        if ir['SessionLapsRemain'] > 5000 and ir['LapLastLapTime'] > 1:
            LapsRemain = round(ir['SessionTimeRemain'] / ir['LapLastLapTime'], 0)
        elif ir['SessionLapsRemain'] <= 0:
            LapsRemain = 1
        else:
            LapsRemain = ir['SessionLapsRemain'] + 1
        FuelUsed = state.last_fuel_level - state.fuel_level
        FuelUsedReq = state.fuel_level / LapsRemain
        FuelLaps = state.fuel_level / FuelUsed
        FuelMPG = state.lap_distance / FuelUsed
        FuelMPGReq = (state.lap_distance * LapsRemain) / state.fuel_level
        FuelLevelReq = (LapsRemain * FuelUsed) - state.fuel_level
        if LapsCompleted <= ir['SessionLapsTotal']:
            print("Lap ", LapsCompleted, " Report [Laps: ", round(FuelLaps, 2), " | Used: ", round(FuelUsed, 3), "gal | Used Rate Req: ", round(FuelUsedReq, 3), "gal | MPG: ", round(FuelMPG, 2), "mpg | MPG Req: ", round(FuelMPGReq, 2), "mpg | Total: ", round(FuelLevelReq, 3), "gal]", sep='', file = output)
        # print(ir['SessionLapsTotal'], ir['LapCompleted'], state.lap_trigger)
        subprocess.call('cmd /c "C:\Program Files (x86)\VoiceAttack\VoiceAttack.exe" -Command external_variables -PassedDecimal ' +(str(round(FuelLaps, 2)))+ ";" +(str(round(FuelUsed, 3)))+ ";" +(str(round(FuelUsedReq, 3)))+ ";" +(str(round(FuelMPG, 2)))+ ";" +(str(round(FuelMPGReq, 2)))+ ";" +(str(round(FuelLevelReq, 3))), startupinfo=si)
        if ir['CarIdxPaceLine'][state.driver_idx] == -1 and ir['CarIdxTrackSurface'][state.driver_idx] == 3 and SessionType == "Race" and ir['SessionState'] == 4 and FuelUsed > 0:
            subprocess.call('cmd /c "C:\Program Files (x86)\VoiceAttack\VoiceAttack.exe" -Command fuel_read', startupinfo=si)
        setattr(State, "last_fuel_level", state.fuel_level)
        state.trigger = False
    output.flush()

if __name__ == '__main__':
    # Initializing ir and State
    ir = irsdk.IRSDK()
    state = State()
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    try:
        # Check connection and start (or not) loop
        while True:
            check_iracing()
            if state.ir_connected:
                loop()
            # Data read delay (min 1/60)
            time.sleep(1 / 60)
    except KeyboardInterrupt:
        pass