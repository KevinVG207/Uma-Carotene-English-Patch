import util
import json
import copy
import os
import argparse
import sys

default_settings = {
    'client_version': None,
    'installed_version': None,
    'dll_name': None,
    'dll_version': None,
    'installed': False,
    'install_started': False,
    'tlg_config_bak': None,
    'prerelease': False,
    'tlg_orig_name': None,
    'patch_customization': {},
    'patch_customization_enabled': False,
    'customization_changed': False,
    'dxgi_backup': False,
    'cellar_downloaded': False,
    'first_run': True,
}

class Settings:
    _path = util.SETTINGS_PATH

    def __init__(self):
        self.args = self._parse_args()

    @property
    def first_run(self):
        return self['first_run']
    
    @first_run.setter
    def first_run(self, value):
        self['first_run'] = value

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

    @property
    def tlg_config_bak(self):
        return self['tlg_config_bak']
    
    @tlg_config_bak.setter
    def tlg_config_bak(self, value):
        self['tlg_config_bak'] = value

    @property
    def prerelease(self):
        return self['prerelease']
    
    @prerelease.setter
    def prerelease(self, value):
        self['prerelease'] = value

    @property
    def tlg_orig_name(self):
        return self['tlg_orig_name']
    
    @tlg_orig_name.setter
    def tlg_orig_name(self, value):
        self['tlg_orig_name'] = value

    @property
    def patch_customization(self):
        return self['patch_customization']
    
    @patch_customization.setter
    def patch_customization(self, value):
        self['patch_customization'] = value

    @property
    def patch_customization_enabled(self):
        return self['patch_customization_enabled']
    
    @patch_customization_enabled.setter
    def patch_customization_enabled(self, value):
        self['patch_customization_enabled'] = value

    @property
    def customization_changed(self):
        return self['customization_changed']
    
    @customization_changed.setter
    def customization_changed(self, value):
        self['customization_changed'] = value
    
    @property
    def dxgi_backup(self):
        return self['dxgi_backup']

    @dxgi_backup.setter
    def dxgi_backup(self, value):
        self['dxgi_backup'] = value
    
    @property
    def cellar_downloaded(self):
        return self['cellar_downloaded']

    @cellar_downloaded.setter
    def cellar_downloaded(self, value):
        self['cellar_downloaded'] = value
    
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
    
    def _parse_args(self):
        p = argparse.ArgumentParser()
        p.add_argument('-U', '--update', action='store_true', help="Auto-update the patcher")
        p.add_argument('-p', '--patch', help="Auto-install the patch if needed with DLL name as argument")
        p.add_argument('-f', '--force', help="Force install the patch even if there's no update. DLL name as argument")
        p.add_argument('-u', '--unpatch', action='store_true', help="Uninstall the patch")
        p.add_argument('-c', '--customization', action='store_true', help="Show the customization widget")

        return p.parse_args()
    
    def has_args(self):
        if len(sys.argv) > 1:
            return True
        return False

settings = Settings()

def pc(cust_setting):
    # Get the patch customization setting
    if settings.patch_customization_enabled:
        # If patch customization is enabled, return the value of the setting
        return settings.patch_customization.get(cust_setting, True)
    
    # Customization is disabled, always True
    return True

def filter_mdb_jsons(mdb_jsons):
    filters = {
        'skill_names': [j for j in mdb_jsons if j.endswith('\\text_data\\47.json')],
        'skill_descs': [j for j in mdb_jsons if j.endswith('\\text_data\\48.json')],
    }
    
    filtered_jsons = set()
    for jsons in filters.values():
        for json in jsons:
            filtered_jsons.add(json)
    
    other = set(mdb_jsons) - filtered_jsons

    filters['mdb'] = other

    selected = set()

    for key, value in filters.items():
        if pc(key):
            selected.update(set(value))
    
    return list(selected)