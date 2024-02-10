# In case more metadata is added in the future, we need to keep track of the version of the intermediate files.
import util
from ui.update_widget import update_widget, update_wait_widget
import urllib.request
import subprocess
import time
import os
import threading
import sys
from urllib.parse import urlparse
from settings import settings

VERSION = (0, 2, 3)

def version_to_string(version):
    return "v" + ".".join(str(v) for v in version)

def string_to_version(version_string):
    if version_string.startswith("v"):
        version_string = version_string[1:]
    
    return tuple(int(v) for v in version_string.split("."))

def check_update():
    if util.is_script:
        # Don't check for updates if we're running as a script
        return
    
    latest_release = util.fetch_latest_github_release('KevinVG207', 'Uma-Carotene-English-Patch', settings.prerelease)

    latest_version = string_to_version(latest_release['tag_name'])

    if VERSION >= latest_version:
        # We're up to date
        return
    
    choice = [False]
    util.run_widget(update_widget, latest_release['tag_name'], choice)
    choice = choice[-1]

    print(choice)

    if not choice:
        return
    
    # Find the asset
    dl_asset = None
    for asset in latest_release['assets']:
        if asset['name'] == "CarotenePatcher.exe":
            dl_asset = asset
            break
    
    if not dl_asset:
        raise Exception("No patcher exe found")

    update_object = Updater(dl_asset['browser_download_url'])
    update_thread = threading.Thread(target=update_object.run)
    update_thread.start()

    util.run_widget(update_wait_widget, update_object)

    # If all went well, we should never reach this point.
    raise Exception("Update failed")


class Updater():
    assets = None
    close_me = False
    def __init__(self, url):
        self.url = url

    def run(self):
        download_url = self.url
        parsed = urlparse(download_url)
        if parsed.scheme != "https":
            print(f"Download URL is not HTTPS! {download_url}")
            self.close_me = True
            return
        try:
            path_to_exe = sys.argv[0]
            exe_file = os.path.basename(path_to_exe)
            without_ext = os.path.splitext(exe_file)[0]

            print(f"Attempting to download from {download_url}")
            urllib.request.urlretrieve(download_url, f"{exe_file}_")
            # Start a process that starts the new exe.
            print("Download complete, now trying to open the new exec.")
            sub = subprocess.Popen(f"taskkill /F /IM \"{exe_file}\" && move /y \".\\{exe_file}\" \".\\{without_ext}.old\" && move /y \".\\{exe_file}_\" \".\\{exe_file}\" && \".\\{exe_file}\"", shell=True)
            while True:
                # Check if subprocess is still running
                if sub.poll() is not None:
                    # Subprocess is done, but we should never reach this point.
                    self.close_me = True
                    return
                time.sleep(1)
        except Exception as e:
            print(e)
            self.close_me = True
            return
