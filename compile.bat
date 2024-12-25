@echo off
set arg=%1
shift

@RD /S /Q ".\build"

@RD /S /Q ".\dist"

pyinstaller --onefile %arg%

xcopy ".\icon.ico" ".\dist"

xcopy ".\LICENSE" ".\dist"

xcopy ".\README.md" ".\dist"

rename ".\dist\main.exe" iR_Fuel_Companion.exe

"C:\Program Files (x86)\Resource Hacker\ResourceHacker.exe" -open ".\dist\iR_Fuel_Companion.exe" -save ".\dist\iR_Fuel_Companion.exe" -action addoverwrite -resource "icon.ico" -mask ICONGROUP,1,0

mkdir .\dist\installer

"C:\Program Files (x86)\Install Creator\ic.exe" /B .\Install.iit

exit