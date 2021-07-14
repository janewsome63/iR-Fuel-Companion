# From https://stackoverflow.com/questions/15128225/python-script-to-read-and-write-a-path-to-registry

#Python3 version of hugo24's snippet
import winreg

def set_reg(path, name, value):
    try:
        REG_PATH = path
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, 
                                       winreg.KEY_WRITE)
        winreg.SetValueEx(registry_key, name, 0, winreg.REG_DWORD, value)
        winreg.CloseKey(registry_key)
        return True
    except WindowsError:
        return False

def get_reg(path, name):
    try:
        REG_PATH = path
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                                       winreg.KEY_READ)
        value, regtype = winreg.QueryValueEx(registry_key, name)
        winreg.CloseKey(registry_key)
        return value
    except WindowsError:
        return None

#Read value 
#print(get_reg('Software\\3CR Setup Downloader', 'Python'))

#Set Value
#set_reg('Software\\3CR Setup Downloader', 'Python', str(63))

