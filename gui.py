import PySimpleGUI as sg
import os
import time
import threading
import sys
import subprocess
import webbrowser

class vars():
    auto_fuel = True
    fuel_max = False
    fuel_pad = 2
    fuel_read = True
    practice_laps = 250
    practice_fuelpct = 100
    window = ""

class binds():
    key_currentpace = ""
    key_currentpace_name = "Bind"
    record_key_currentpace = False
    key_tofinish = ""
    key_tofinish_name = "Bind"
    record_key_tofinish = False
    key_setrequired = ""
    key_setrequired_name = "Bind"
    record_key_setrequired = False
    key_fuelread = ""
    key_fuelread_name = "Bind"
    record_key_fuelread = False
    key_maxusage = ""
    key_maxusage_name = "Bind"
    record_key_maxusage = False
    key_autofuel = ""
    key_autofuel_name = "Bind"
    record_key_autofuel = False

def event(name, value):
    vars.window.write_event_value(name, value)

def main(version):
    sg.theme('LightGray1')

    fueling = [  [sg.Push(), sg.Text(text = "Fueling:"), sg.Push()],
                 [sg.Checkbox('Auto Fueling', default = vars.auto_fuel, key = '-FuelAuto-', enable_events = True)],
                 [sg.Checkbox('Use Max Usage Data', default = vars.fuel_max, key = '-FuelMax-', enable_events = True)],
                 [sg.Text(text = "Extra Laps of Fuel:"), sg.Spin(values=[i for i in range(0, 26)], initial_value = vars.fuel_pad, key = '-FuelPad-', enable_events = True)]  ]

    speech = [  [sg.Push(), sg.Text(text = "Speech:"), sg.Push()],
                [sg.Checkbox('TTS Fuel Updates', default = vars.fuel_read, key = '-FuelRead-', enable_events = True)]  ]

    practice = [  [sg.Push(), sg.Text(text = "Practice:"), sg.Push()],
                  [sg.Text(text = "Laps for Practice Races:"), sg.Push(), sg.Spin(values=[i for i in range(1, 1000)], initial_value = vars.practice_laps, key = '-PracLaps-', enable_events = True)],
                  [sg.Text(text = "Fuel % for Practice Races:"), sg.Push(), sg.Spin(values=[i for i in range(1, 101)], initial_value = vars.practice_fuelpct, key = '-PracFuelPct-', enable_events = True)]  ]

    keybinds = [  [sg.Push(), sg.Text(text = "Keybinds:"), sg.Push()],
                  [sg.Text(text = "Print Current Pace Info:"), sg.Push(), sg.Button(binds.key_currentpace_name, key = '-BindCurrentPace-', enable_events = True)],
                  [sg.Text(text = "Print Fuel to Finish Info:"), sg.Push(), sg.Button(binds.key_tofinish_name, key = '-BindToFinish-', enable_events = True)],
                  [sg.Text(text = "Set Fuel to Required:"), sg.Push(), sg.Button(binds.key_setrequired_name, key = '-BindSetRequired-', enable_events = True)],
                  [sg.Text(text = "Toggle TTS Fuel Updates:"), sg.Push(), sg.Button(binds.key_fuelread_name, key = '-BindFuelRead-', enable_events = True)],
                  [sg.Text(text = "Toggle Max Usage Data:"), sg.Push(), sg.Button(binds.key_maxusage_name, key = '-BindMaxUsage-', enable_events = True)],
                  [sg.Text(text = "Toggle Auto Fueling:"), sg.Push(), sg.Button(binds.key_autofuel_name, key = '-BindAutoFuel-', enable_events = True)]  ]
    
    github = [  [sg.Button("Open GitHub Page", key = '-OpenGitHub-', enable_events = True)]  ]

    open_logs = [  [sg.Button("Open Logs Folder", key = '-OpenLogs-', enable_events = True)]  ]

    settings_layout = [  [sg.Column(fueling, vertical_alignment = 'top'), sg.VerticalSeparator(), sg.Column(speech, vertical_alignment = 'top'), sg.VerticalSeparator(), sg.Column(practice, vertical_alignment = 'top'), sg.VerticalSeparator(), sg.Column(keybinds, vertical_alignment = 'top')],
                         [sg.VPush()],
                         [sg.Column(github, justification = 'left'), sg.Push(), sg.Column(open_logs, justification = 'right')]  ]

    logging_layout = [  [sg.Multiline(autoscroll = True, reroute_stdout = True, echo_stdout_stderr = True, enter_submits = False, key='-Log-', expand_x=True, expand_y=True, pad = (5,5), font = ('Fixedsys'))]  ]

    layout = [  ]

    layout +=[  [sg.TabGroup([[  sg.Tab('Logging', logging_layout),
                               sg.Tab('Settings', settings_layout)]], key='-Tabs-', expand_x=True, expand_y=True),]  ]

    window = sg.Window('iR Fuel Companion ' + version, layout, icon='icon.ico', size=(1080, 500), resizable=True, finalize=True,)

    vars.window = window

    window.set_min_size((200, 200))

    while True:
        event, values = window.Read()
        if event == sg.WIN_CLOSED:
            break

        if event == '-FuelAuto-':
            if values['-FuelAuto-'] == 1:
                vars.auto_fuel = True
                window['-FuelAuto-'].update(vars.auto_fuel)
            else:
                vars.auto_fuel= False
                window['-FuelAuto-'].update(vars.auto_fuel)
        if event == '-FuelMax-':
            if values['-FuelMax-'] == 1:
                vars.fuel_max = True
                window['-FuelMax-'].update(vars.fuel_max)
            else:
                vars.fuel_max = False
                window['-FuelMax-'].update(vars.fuel_max)
        if event == '-FuelRead-':
            if values['-FuelRead-'] == 1:
                vars.fuel_read = True
                window['-FuelRead-'].update(vars.fuel_read)
            else:
                vars.fuel_read = False
                window['-FuelRead-'].update(vars.fuel_read)

        if event == "-FuelPad-":
            vars.fuel_pad = values['-FuelPad-']
        if event == "-PracLaps-":
            vars.practice_laps = values['-PracLaps-']
        if event == "-PracFuelPct-":
            vars.practice_fuelpct = values['-PracFuelPct-']

        if event == '-BindCurrentPace-':
            if binds.key_currentpace_name == "<-Recording->":
                binds.record_key_currentpace = False
                binds.key_currentpace_name = "Bind"
            elif binds.record_key_currentpace == True and binds.key_currentpace_name != "Bind":
                binds.record_key_currentpace = False
            else:
                binds.record_key_currentpace = True
            time.sleep(0.1)
            window['-BindCurrentPace-'].update(binds.key_currentpace_name)
        if event == '-BindToFinish-':
            if binds.key_tofinish_name == "<-Recording->":
                binds.record_key_tofinish = False
                binds.key_tofinish_name = "Bind"
            elif binds.record_key_tofinish == True and binds.key_tofinish_name != "Bind":
                binds.record_key_tofinish = False
            else:
                binds.record_key_tofinish = True
            time.sleep(0.1)
            window['-BindToFinish-'].update(binds.key_tofinish_name)
        if event == '-BindSetRequired-':
            if binds.key_setrequired_name == "<-Recording->":
                binds.record_key_setrequired = False
                binds.key_setrequired_name = "Bind"
            elif binds.record_key_setrequired == True and binds.key_setrequired_name != "Bind":
                binds.record_key_setrequired = False
            else:
                binds.record_key_setrequired = True
            time.sleep(0.1)
            window['-BindSetRequired-'].update(binds.key_setrequired_name)
        if event == '-BindFuelRead-':
            if binds.key_fuelread_name == "<-Recording->":
                binds.record_key_fuelread = False
                binds.key_fuelread_name = "Bind"
            elif binds.record_key_fuelread == True and binds.key_fuelread_name != "Bind":
                binds.record_key_fuelread = False
            else:
                binds.record_key_fuelread = True
            time.sleep(0.1)
            window['-BindFuelRead-'].update(binds.key_fuelread_name)
        if event == '-BindMaxUsage-':
            if binds.key_maxusage_name == "<-Recording->":
                binds.record_key_maxusage = False
                binds.key_maxusage_name = "Bind"
            elif binds.record_key_maxusage == True and binds.key_maxusage_name != "Bind":
                binds.record_key_maxusage = False
            else:
                binds.record_key_maxusage = True
            time.sleep(0.1)
            window['-BindMaxUsage-'].update(binds.key_maxusage_name)
        if event == '-BindAutoFuel-':
            if binds.key_autofuel_name == "<-Recording->":
                binds.record_key_autofuel = False
                binds.key_autofuel_name = "Bind"
            elif binds.record_key_autofuel == True and binds.key_autofuel_name != "Bind":
                binds.record_key_autofuel = False
            else:
                binds.record_key_autofuel = True
            time.sleep(0.1)
            window['-BindAutoFuel-'].update(binds.key_autofuel_name)
        if event == '-OpenLogs-':
            subprocess.Popen(r'explorer ".\logs"')
        if event == '-OpenGitHub-':
            webbrowser.open("https://github.com/janewsome63/iR-Fuel-Companion")
        time.sleep(0.1)
    window.close()
