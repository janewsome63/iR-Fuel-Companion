import _tkinter
import configparser
import PySimpleGUI as Sg
import subprocess
import time
import webbrowser


class Vars:
    user_dir = ""
    window = ""
    checkboxes = {
        "auto_fuel": True,
        "check_updates": True,
        "engine_warnings": True,
        "tts_fuel": True,
        "txt_fuel": True,
        "temp_updates": True,
    }
    combo = {
        "auto_fuel_type": "Average",
    }
    input = {
        "fixed_usage": 0.0,
        "oil_threshold": 0,
        "water_threshold": 0,
    }
    spin = {
        "extra_laps": 2,
        "practice_laps": 250,
        "practice_fuel_percent": 100,
    }


class Binds:
    binding = False
    pause_count = 0
    keys = {
        "auto_fuel": "",
        "auto_fuel_cycle": "",
        "auto_fuel_average": "",
        "auto_fuel_max": "",
        "auto_fuel_fixed": "",
        "set_required": "",
        "tts_fuel": "",
        "txt_fuel": "",
        "temp_updates": "",
        "temp_report": "",
        "previous_usage": "",
        "required_usage": "",
    }
    names = {
        "auto_fuel": "Bind",
        "auto_fuel_cycle": "Bind",
        "auto_fuel_average": "Bind",
        "auto_fuel_max": "Bind",
        "auto_fuel_fixed": "Bind",
        "set_required": "Bind",
        "tts_fuel": "Bind",
        "txt_fuel": "Bind",
        "temp_updates": "Bind",
        "temp_report": "Bind",
        "previous_usage": "Bind",
        "required_usage": "Bind",
    }
    recording = {
        "auto_fuel": False,
        "auto_fuel_cycle": False,
        "auto_fuel_average": False,
        "auto_fuel_max": False,
        "auto_fuel_fixed": False,
        "set_required": False,
        "tts_fuel": False,
        "txt_fuel": False,
        "temp_updates": False,
        "temp_report": False,
        "previous_usage": False,
        "required_usage": False,
    }


# Write to settings.ini
def set_config():
    config = configparser.ConfigParser()
    config['Fueling'] = {
        'auto_fuel': Vars.checkboxes["auto_fuel"],
        'auto_fuel_type': Vars.combo["auto_fuel_type"],
        'fixed_usage': Vars.input["fixed_usage"],
        'extra_laps': Vars.spin["extra_laps"],
    }
    config['Updates'] = {
        'check_updates': Vars.checkboxes["check_updates"],
        'engine_warnings': Vars.checkboxes["engine_warnings"],
        'oil_threshold': Vars.input["oil_threshold"],
        'water_threshold': Vars.input["water_threshold"],
        'tts_fuel': Vars.checkboxes["tts_fuel"],
        'txt_fuel': Vars.checkboxes["txt_fuel"],
        'temp_updates': Vars.checkboxes["temp_updates"],
    }
    config['Practice'] = {
        'laps': Vars.spin["practice_laps"],
        'fuel_percent': Vars.spin["practice_fuel_percent"],
    }
    config['Controls'] = {
        'auto_fuel_toggle': Binds.keys["auto_fuel"],
        'auto_fuel_cycle': Binds.keys["auto_fuel_cycle"],
        'auto_fuel_average': Binds.keys["auto_fuel_average"],
        'auto_fuel_max': Binds.keys["auto_fuel_max"],
        'auto_fuel_fixed': Binds.keys["auto_fuel_fixed"],
        'set_required': Binds.keys["set_required"],
        'tts_fuel': Binds.keys["tts_fuel"],
        'txt_fuel': Binds.keys["txt_fuel"],
        'temp_updates': Binds.keys["temp_updates"],
        'temp_report': Binds.keys["temp_report"],
        'previous_usage': Binds.keys["previous_usage"],
        'required_usage': Binds.keys["required_usage"],
    }
    with open(Vars.user_dir + '\\settings.ini', 'w') as configfile:
        config.write(configfile)


def event(name, value):
    Vars.window.write_event_value(name, value)


def main(version):
    Sg.theme('LightGray1')
    right_click_menu = ['', ['Copy', 'Select All']]
    fueling = [
        [Sg.Push(), Sg.Text(text="Fueling:"), Sg.Push()],
        [Sg.Checkbox('Auto Fuel', default=Vars.checkboxes["auto_fuel"], key='check-auto_fuel', enable_events=True)],
        [Sg.Text(text="Auto Fuel Type:"), Sg.Combo(['Average', 'Max', 'Fixed'], default_value=Vars.combo["auto_fuel_type"], readonly=True, key='combo-auto_fuel_type', enable_events=True)],
        [Sg.Text(text="Fixed Usage Per Lap:"), Sg.InputText(Vars.input["fixed_usage"], size=(5, 1), key='input_float-fixed_usage', enable_events=True)],
        [Sg.Text(text="Extra Laps of Fuel:"), Sg.Spin(values=[i for i in range(0, 26)], initial_value=Vars.spin["extra_laps"], key='spin-extra_laps', enable_events=True)],
    ]
    speech = [
        [Sg.Push(), Sg.Text(text="Alerts & System:"), Sg.Push()],
        [Sg.Checkbox('Check for Updates', default=Vars.checkboxes["check_updates"], key='check-check_updates', enable_events=True)],
        [Sg.Checkbox('Engine Warnings', default=Vars.checkboxes["engine_warnings"], key='check-engine_warnings', enable_events=True)],
        [Sg.Text(text="Oil Threshold:"), Sg.InputText(Vars.input["oil_threshold"], size=(5, 1), key='input_float-oil_threshold', enable_events=True)],
        [Sg.Text(text="Water Threshold:"), Sg.InputText(Vars.input["water_threshold"], size=(5, 1), key='input_float-water_threshold', enable_events=True)],
        [Sg.Checkbox('Fuel (TTS)', default=Vars.checkboxes["tts_fuel"], key='check-tts_fuel', enable_events=True)],
        [Sg.Checkbox('Fuel (Text)', default=Vars.checkboxes["txt_fuel"], key='check-txt_fuel', enable_events=True)],
        [Sg.Checkbox('Temperature', default=Vars.checkboxes["temp_updates"], key='check-temp_updates', enable_events=True)],
    ]
    practice = [
        [Sg.Push(), Sg.Text(text="Practice:"), Sg.Push()],
        [Sg.Text(text="Laps for Practice Races:"), Sg.Push(), Sg.Spin(values=[i for i in range(1, 1000)], initial_value=Vars.spin["practice_laps"], key='spin-practice_laps', enable_events=True)],
        [Sg.Text(text="Fuel % for Practice Races:"), Sg.Push(), Sg.Spin(values=[i for i in range(1, 101)], initial_value=Vars.spin["practice_fuel_percent"], key='spin-practice_fuel_percent', enable_events=True)],
    ]
    keybindings = [
        [Sg.Push(), Sg.Text(text="Keybindings:"), Sg.Push()],
        [Sg.Text(text="Toggle Auto Fuel:"), Sg.Push(), Sg.Button(Binds.names["auto_fuel"], key='bind-auto_fuel', enable_events=True)],
        [Sg.Text(text="Cycle Auto Fuel Type:"), Sg.Push(), Sg.Button(Binds.names["auto_fuel_cycle"], key='bind-auto_fuel_cycle', enable_events=True)],
        [Sg.Text(text="Switch to Average:"), Sg.Push(), Sg.Button(Binds.names["auto_fuel_average"], key='bind-auto_fuel_average', enable_events=True)],
        [Sg.Text(text="Switch to Max:"), Sg.Push(), Sg.Button(Binds.names["auto_fuel_max"], key='bind-auto_fuel_max', enable_events=True)],
        [Sg.Text(text="Switch to Fixed:"), Sg.Push(), Sg.Button(Binds.names["auto_fuel_fixed"], key='bind-auto_fuel_fixed', enable_events=True)],
        [Sg.Text(text="Set Fuel to Required:"), Sg.Push(), Sg.Button(Binds.names["set_required"], key='bind-set_required', enable_events=True)],
        [Sg.Text(text="Toggle TTS Fuel Updates:"), Sg.Push(), Sg.Button(Binds.names["tts_fuel"], key='bind-tts_fuel', enable_events=True)],
        [Sg.Text(text="Toggle Text Fuel Updates:"), Sg.Push(), Sg.Button(Binds.names["txt_fuel"], key='bind-txt_fuel', enable_events=True)],
        [Sg.Text(text="Toggle Temperature Updates:"), Sg.Push(), Sg.Button(Binds.names["temp_updates"], key='bind-temp_updates', enable_events=True)],
        [Sg.Text(text="Report Current Temperature:"), Sg.Push(), Sg.Button(Binds.names["temp_report"], key='bind-temp_report', enable_events=True)],
        [Sg.Text(text="Print Previous Lap Info:"), Sg.Push(), Sg.Button(Binds.names["previous_usage"], key='bind-previous_usage', enable_events=True)],
        [Sg.Text(text="Print Required Usage Info:"), Sg.Push(), Sg.Button(Binds.names["required_usage"], key='bind-required_usage', enable_events=True)],
    ]
    github = [
        [Sg.Button("View Releases", key='other-releases', enable_events=True)],
    ]
    open_logs = [
        [Sg.Button("Open Logs", key='other-logs', enable_events=True)],
    ]
    settings_layout = [
        [Sg.Column(fueling, vertical_alignment='top'), Sg.VerticalSeparator(), Sg.Column(speech, vertical_alignment='top'), Sg.VerticalSeparator(), Sg.Column(practice, vertical_alignment='top'), Sg.VerticalSeparator(),
         Sg.Column(keybindings, vertical_alignment='top')],
        [Sg.VPush()],
        [Sg.Column(github, justification='left'), Sg.Push(), Sg.Column(open_logs, justification='right')],
    ]
    logging_layout = [
        [Sg.Multiline(autoscroll=True, reroute_stdout=True, reroute_stderr=True, echo_stdout_stderr=True, enter_submits=False, enable_events=False, disabled=True, right_click_menu=right_click_menu, key='multiline-log', expand_x=True, expand_y=True,
                      pad=(5, 5), font='Fixedsys')],
    ]
    layout = []
    layout += [
        [Sg.TabGroup([[Sg.Tab('Logging', logging_layout), Sg.Tab('Settings', settings_layout)]], key='tabgroup-tabs', expand_x=True, expand_y=True)],
    ]
    window = Sg.Window('iR Fuel Companion ' + version, layout, icon='icon.ico', size=(1165, 500), resizable=True, finalize=True)
    Vars.window = window
    window.set_min_size((200, 200))

    log: Sg.Multiline = window['multiline-log']

    while True:
        trigger, values = window.Read()
        if trigger == Sg.WIN_CLOSED:
            break
        if trigger in right_click_menu[1]:
            if trigger == "Copy":
                try:
                    text = log.Widget.selection_get()
                    window.TKroot.clipboard_clear()
                    window.TKroot.clipboard_append(text)
                except _tkinter.TclError:
                    pass
            if trigger == "Select All":
                log.Widget.selection_clear()
                log.Widget.tag_add('sel', '1.0', 'end')
            option = "None"
        else:
            split = trigger.split('-')
            option = split[1]
        if "spin" in trigger:
            Vars.spin[option] = values[trigger]
        elif "combo" in trigger:
            Vars.combo[option] = values[trigger]
            window[trigger].update(value=Vars.combo[option])
        elif "input_float" in trigger:
            try:
                Vars.input[option] = float(values[trigger])
            except ValueError:
                Vars.input[option] = 0.0
        elif "check" in trigger:
            if values[trigger] == 1:
                Vars.checkboxes[option] = True
            else:
                Vars.checkboxes[option] = False
            window[trigger].update(Vars.checkboxes[option])
        elif "bind" in trigger:
            if Binds.names[option] == "<-Recording->":
                Binds.keys[option] = ""
                Binds.binding = False
                Binds.names[option] = "Bind"
                Binds.recording[option] = False
            elif Binds.recording[option] and Binds.names[option] != "Bind":
                Binds.binding = False
                Binds.pause_count = 1
                Binds.recording[option] = False
            else:
                Binds.binding = True
                Binds.recording[option] = True
                Binds.names[option] = "<-Recording->"
            window[trigger].update(Binds.names[option])
        if trigger == 'other-logs':
            subprocess.Popen('explorer ' + Vars.user_dir + '\\logs')
        if trigger == 'other-releases':
            webbrowser.open("https://github.com/janewsome63/iR-Fuel-Companion/releases")
        set_config()
        time.sleep(0.1)
    window.close()
