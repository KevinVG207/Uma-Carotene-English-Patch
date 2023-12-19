import util
import json
import copy
import os

default_settings = {
    'installed_version': None,
    'dll_name': None
}

class Settings:
    _path = util.SETTINGS_PATH
    
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