import _tkinter
import configparser
import decimal
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
        "usage_high": 0.0,
        "usage_low": 0.0,
        "oil_threshold": 0,
        "practice_fuel_percent": 100,
        "practice_laps": 0,
        "water_threshold": 0,
    }
    spin = {
        "extra_laps": 2,
    }
    other = {
        "oil_reset": False,
        "water_reset": False,
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
        "auto_fuel_info": "",
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
        "auto_fuel_info": "Bind",
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
        "auto_fuel_info": False,
    }


lang = {
    "auto_fuel": "Toggles auto fuel on or off",
    "auto_fuel_type": "The calculation type used. \"Average\" uses the usage of the last five clean laps, \"Max\" uses the maximum clean lap usage recorded, \"Fixed\" uses the fixed usage defined below",
    "usage_high": "Optional, 0 to disable. The usage to be used in the \"Fixed\" type's calculations and for informational purposes, shown in the required usage in-game print-out. Can be either liters or gallons, depending on your in-sim displayed units",
    "usage_low": "Optional, 0 to disable. Purely informational, shown in the required usage in-game print-out. Can be either liters or gallons, depending on your in-sim displayed units",
    "extra_laps": "Extra laps of fuel to add as a buffer",
    "check_updates": "Toggle update checking. If enabled, an alert will be printed and spoken through text-to-speech notifying you of a newer release, if available",
    "engine_warnings": "Toggle alerts for engine related warnings. Currently, this only alerts of high oil and water temperatures",
    "oil_threshold": "The oil temperature at which you'll be warned. If 0, the built-in iRacing threshold will be used instead. Can be either celsius or fahrenheit, depending on your in-sim displayed units",
    "water_threshold": "The water temperature at which you'll be warned. If 0, the built-in iRacing threshold will be used instead. Can be either celsius or fahrenheit, depending on your in-sim displayed units",
    "tts_fuel": "Toggles text-to-speech fuel updates every lap",
    "txt_fuel": "Toggles printing fuel updates to in-sim chat every lap",
    "temp_updates": "Toggles automatic environmental (air and track) temperature updates",
    "practice_laps": "Defines race length during practice sessions, to make it easier to do race simulations. Set this to 0 to disable practice races altogether",
    "practice_fuel_percent": "Sets the max fuel tank percentage during practice races so that calculations are accurate. Will not be used if the sim-defined limit is already below 100%",
    "bind_auto_fuel": "Binding to toggle auto fuel on or off",
    "bind_auto_fuel_cycle": "Binding to cycle through auto fuel calculation types",
    "bind_auto_fuel_average": "Binding to switch directly to \"Average\" auto fuel type",
    "bind_auto_fuel_max": "Binding to switch directly to \"Max\" auto fuel type",
    "bind_auto_fuel_fixed": "Binding to switch directly to \"Fixed\" auto fuel type",
    "bind_set_required": "Binding to set the in-sim fuel to add, as auto fuel would do when pitting service starts. Useful for when auto fuel is disabled",
    "bind_tts_fuel": "Binding to toggle text-to-speech previous lap updates on or off",
    "bind_txt_fuel": "Binding to toggle printing previous lap info to in-sim chat every lap",
    "bind_temp_updates": "Binding to toggle environmental temperature text-to-speech updates on or off",
    "bind_temp_report": "Binding to read aloud current environmental temperatures with text-to-speech",
    "bind_previous_usage": "Binding to print the previous lap's fuel info to in-sim chat",
    "bind_required_usage": "Binding to print required usage info to in-sim chat",
    "bind_auto_fuel_info": "Binding to print auto fueling info to in-sim chat",
}


# Write to settings.ini
def set_config():
    config = configparser.ConfigParser()
    config['Fueling'] = {
        'auto_fuel': Vars.checkboxes["auto_fuel"],
        'auto_fuel_type': Vars.combo["auto_fuel_type"],
        'usage_high': Vars.input["usage_high"],
        'usage_low': Vars.input["usage_low"],
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
        'laps': Vars.input["practice_laps"],
        'fuel_percent': Vars.input["practice_fuel_percent"],
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
        'auto_fuel_info': Binds.keys["auto_fuel_info"],
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
        [Sg.Checkbox('Auto Fuel', tooltip=lang['auto_fuel'], default=Vars.checkboxes["auto_fuel"], key='check-auto_fuel', enable_events=True)],
        [Sg.Text(text="Auto Fuel Type:", tooltip=lang['auto_fuel_type']), Sg.Combo(["Average", "Max", "Fixed"], default_value=Vars.combo["auto_fuel_type"], readonly=True, key='combo-auto_fuel_type', enable_events=True)],
        [Sg.Text(text="Usage Per Lap (High):", tooltip=lang['usage_high']), Sg.InputText(Vars.input["usage_high"], size=(5, 1), key='input_float-usage_high', enable_events=True)],
        [Sg.Text(text="Usage Per Lap (Low):", tooltip=lang['usage_low']), Sg.InputText(Vars.input["usage_low"], size=(5, 1), key='input_float-usage_low', enable_events=True)],
        [Sg.Text(text="Extra Laps of Fuel:", tooltip=lang['extra_laps']), Sg.Spin(values=[i for i in range(0, 26)], initial_value=Vars.spin["extra_laps"], key='spin-extra_laps', enable_events=True)],
    ]
    speech = [
        [Sg.Push(), Sg.Text(text="Alerts & System:"), Sg.Push()],
        [Sg.Checkbox('Check for Updates', tooltip=lang['check_updates'], default=Vars.checkboxes["check_updates"], key='check-check_updates', enable_events=True)],
        [Sg.Checkbox('Engine Warnings', tooltip=lang['engine_warnings'], default=Vars.checkboxes["engine_warnings"], key='check-engine_warnings', enable_events=True)],
        [Sg.Text(text="Oil Threshold:", tooltip=lang['oil_threshold']), Sg.InputText(Vars.input["oil_threshold"], size=(4, 1), key='input_int-oil_threshold', enable_events=True)],
        [Sg.Text(text="Water Threshold:", tooltip=lang['water_threshold']), Sg.InputText(Vars.input["water_threshold"], size=(4, 1), key='input_int-water_threshold', enable_events=True)],
        [Sg.Checkbox('Fuel (TTS)', tooltip=lang['tts_fuel'], default=Vars.checkboxes["tts_fuel"], key='check-tts_fuel', enable_events=True)],
        [Sg.Checkbox('Fuel (Text)', tooltip=lang['txt_fuel'], default=Vars.checkboxes["txt_fuel"], key='check-txt_fuel', enable_events=True)],
        [Sg.Checkbox('Temperature', tooltip=lang['temp_updates'], default=Vars.checkboxes["temp_updates"], key='check-temp_updates', enable_events=True)],
    ]
    practice = [
        [Sg.Push(), Sg.Text(text="Practice:"), Sg.Push()],
        [Sg.Text(text="Laps for Practice Races:", tooltip=lang['practice_laps']), Sg.Push(), Sg.InputText(Vars.input["practice_laps"], size=(4, 1), key='input_int-practice_laps', enable_events=True)],
        [Sg.Text(text="Fuel % for Practice Races:", tooltip=lang['practice_fuel_percent']), Sg.Push(), Sg.InputText(Vars.input["practice_fuel_percent"], size=(4, 1), key='input_int-practice_fuel_percent', enable_events=True)],
    ]
    keybindings = [
        [Sg.Push(), Sg.Text(text="Keybindings:"), Sg.Push()],
        [Sg.Text(text="Toggle Auto Fuel:", tooltip=lang['bind_auto_fuel']), Sg.Push(), Sg.Button(Binds.names["auto_fuel"], key='bind-auto_fuel', enable_events=True)],
        [Sg.Text(text="Cycle Auto Fuel Type:", tooltip=lang['bind_auto_fuel_cycle']), Sg.Push(), Sg.Button(Binds.names["auto_fuel_cycle"], key='bind-auto_fuel_cycle', enable_events=True)],
        [Sg.Text(text="Switch to Average:", tooltip=lang['bind_auto_fuel_average']), Sg.Push(), Sg.Button(Binds.names["auto_fuel_average"], key='bind-auto_fuel_average', enable_events=True)],
        [Sg.Text(text="Switch to Max:", tooltip=lang['bind_auto_fuel_max']), Sg.Push(), Sg.Button(Binds.names["auto_fuel_max"], key='bind-auto_fuel_max', enable_events=True)],
        [Sg.Text(text="Switch to Fixed:", tooltip=lang['bind_auto_fuel_fixed']), Sg.Push(), Sg.Button(Binds.names["auto_fuel_fixed"], key='bind-auto_fuel_fixed', enable_events=True)],
        [Sg.Text(text="Set Fuel to Required:", tooltip=lang['bind_set_required']), Sg.Push(), Sg.Button(Binds.names["set_required"], key='bind-set_required', enable_events=True)],
        [Sg.Text(text="Toggle TTS Fuel Updates:", tooltip=lang['bind_tts_fuel']), Sg.Push(), Sg.Button(Binds.names["tts_fuel"], key='bind-tts_fuel', enable_events=True)],
        [Sg.Text(text="Toggle Text Fuel Updates:", tooltip=lang['bind_txt_fuel']), Sg.Push(), Sg.Button(Binds.names["txt_fuel"], key='bind-txt_fuel', enable_events=True)],
        [Sg.Text(text="Toggle Temperature Updates:", tooltip=lang['bind_temp_updates']), Sg.Push(), Sg.Button(Binds.names["temp_updates"], key='bind-temp_updates', enable_events=True)],
        [Sg.Text(text="Report Current Temperature:", tooltip=lang['bind_temp_report']), Sg.Push(), Sg.Button(Binds.names["temp_report"], key='bind-temp_report', enable_events=True)],
        [Sg.Text(text="Print Previous Lap Info:", tooltip=lang['bind_previous_usage']), Sg.Push(), Sg.Button(Binds.names["previous_usage"], key='bind-previous_usage', enable_events=True)],
        [Sg.Text(text="Print Required Usage Info:", tooltip=lang['bind_required_usage']), Sg.Push(), Sg.Button(Binds.names["required_usage"], key='bind-required_usage', enable_events=True)],
        [Sg.Text(text="Print Auto Fuel Info:", tooltip=lang['bind_auto_fuel_info']), Sg.Push(), Sg.Button(Binds.names["auto_fuel_info"], key='bind-auto_fuel_info', enable_events=True)],
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
        elif "input_int" in trigger:
            if "laps" in trigger:
                low = 0
                high = 9999
            elif "fuel_percent" in trigger:
                low = 1
                high = 100
            elif "threshold" in trigger:
                low = 0
                high = 999
            else:
                low = -32767
                high = 32767
            try:
                value = int(values[trigger])
                if " " in str(values[trigger]):
                    raise ValueError
                if value < low:
                    window[trigger].update(value=low)
                    Vars.input[option] = low
                elif value > high:
                    window[trigger].update(value=high)
                    Vars.input[option] = high
                else:
                    Vars.input[option] = value
            except ValueError:
                if values[trigger] != "" and values[trigger] != "-":
                    window[trigger].update(value=Vars.input[option])

        elif "input_float" in trigger:
            try:
                value = float(values[trigger])
                digits = decimal.Decimal(values[trigger]).as_tuple().exponent
                if value < 0 or digits < -3 or " " in str(values[trigger]):
                    raise ValueError
                else:
                    Vars.input[option] = float(values[trigger])
                if str(values[trigger]).startswith("."):
                    window[trigger].update(value=Vars.input[option])
            except ValueError:
                if values[trigger] != "" and values[trigger] != "." and values[trigger] != "-":
                    window[trigger].update(value=Vars.input[option])
                elif values[trigger] == ".":
                    window[trigger].update(value="0.")
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
