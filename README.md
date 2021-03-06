# iR-Fuel-Companion
Python script for iRacing to help you manage your fuel strategy and log strategy info. 

# Standalone Installation
Download and run the installer from the latest release. Before launching the program be sure to set it to run as an administrator, it will not work otherwise.

# Features
* On each completed lap, it reads aloud using text-to-speech your previous lap's fuel usage and your remaining laps based on that usage. 
* Sets your fuel automatically when you stop in your box. It will immediately stop fueling once the required amount has been reached. You can set auto fuel to use either the average usage of your last five green flag laps, or to use your max usage to that point in the race. You can also disable auto fueling entirely and use a hotkey to trigger setting fuel to the required amount. 
* There are two hotkeys for printing fuel info to in-game chat, visible only to you. The "current pace" hotkey prints the remaining laps in stint, fuel usage, fuel economy and required total amount that needs to be added, all based on the data from the last completed lap. The "fuel to finish" hotkey prints the remaining laps in race, required per lap usage and economy in order to finish the race from that point without pitting, and shows the required fuel to be added based on both average and max usage data.
* During practice or test sessions, the GUI options for race laps and max fuel percent are used for race simulation. The mock race will end when you exit the car or tow. These are entirely ignored in the race. 
* Strategy info such as tire wear, lap times, fuel, etc are printed in the GUI for easy copying and sharing with teammates. These logs are also stored in the program's install directory in the "logs" folder. 

To be continued...
