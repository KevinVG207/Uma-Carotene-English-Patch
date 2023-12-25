import util
import json
import copy
import os

default_settings = {
    'client_version': None,
    'installed_version': None,
    'dll_name': None,
    'dll_version': None,
    'installed': False,
    'install_started': False
}

class Settings:
    _path = util.SETTINGS_PATH

    @property
    def client_version(self):
        return self['client_version']
    
    @client_version.setter
    def client_version(self, value):
        self['client_version'] = value

    @property
    def install_started(self):
        return self['install_started']
    
    @install_started.setter
    def install_started(self, value):
        self['install_started'] = value

    @property
    def installed(self):
        return self['installed']
    
    @installed.setter
    def installed(self, value):
        self['installed'] = value

    @property
    def installed_version(self):
        return self['installed_version']
    
    @installed_version.setter
    def installed_version(self, value):
        self['installed_version'] = value
    
    @property
    def dll_version(self):
        return self['dll_version']
    
    @dll_version.setter
    def dll_version(self, value):
        self['dll_version'] = value
    
    @property
    def dll_name(self):
        return self['dll_name']
    
    @dll_name.setter
    def dll_name(self, value):
        self['dll_name'] = value
    
    def _load(self):
        # print("Loading settings")
        if not os.path.exists(self._path):
            # print("Settings file not found. Using default.")
            return copy.deepcopy(default_settings)
        
        with open(self._path, 'r') as f:
            tmp = json.load(f)
        
        return tmp
    
    def _save(self, settings):
        # print("Saving settings")
        new_settings = {}
        for key in default_settings:
            if key in settings:
                new_settings[key] = settings[key]
            else:
                new_settings[key] = default_settings[key]

        with open(self._path, 'w') as f:
            json.dump(new_settings, f, indent=4)
    
    def __getitem__(self, key):
        # print(f"Getting setting {key}")
        settings = self._load()

        if key in settings:
            return settings[key]
        
        if key in default_settings:
            return default_settings[key]
        
        return None
    
    def __setitem__(self, key, value):
        # print(f"Setting {key} to {value}")
        settings = self._load()
        settings[key] = value
        self._save(settings)

settings = Settings()