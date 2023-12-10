import sqlite3
import os
import json
import requests
import numpy as np
import shutil
import zipfile
from PIL import Image, ImageFilter
import tqdm as _tqdm
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

relative_dir = os.path.abspath(os.getcwd())
unpack_dir = relative_dir
is_script = True
if hasattr(sys, "_MEIPASS"):
    unpack_dir = sys._MEIPASS
    is_script = False
    relative_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    os.chdir(relative_dir)
is_debug = is_script

def get_relative(relative_path):
    """Gets the absolute path of a file relative to the executable's directory.
    """
    return os.path.join(relative_dir, relative_path)

def get_asset(asset_path):
    """Gets the absolute path of an asset relative to the unpack directory.
    """
    return os.path.join(unpack_dir, asset_path)


TQDM_FORMAT = "{desc}: {percentage:3.0f}% |{bar}|"
TQDM_NCOLS = 65

MDB_PATH = os.path.expandvars("%userprofile%\\appdata\\locallow\\Cygames\\umamusume\\master\\master.mdb")
META_PATH = os.path.expandvars("%userprofile%\\appdata\\locallow\\Cygames\\umamusume\\meta")

DATA_PATH = os.path.expandvars("%userprofile%\\appdata\\locallow\\Cygames\\umamusume\\dat")

TL_PREFIX = "translations\\"
INTERMEDIATE_PREFIX = "editing\\"

MDB_FOLDER = TL_PREFIX + "mdb\\"
MDB_FOLDER_EDITING = INTERMEDIATE_PREFIX + "mdb\\"

ASSETS_FOLDER = TL_PREFIX + "assets\\"
ASSETS_FOLDER_EDITING = INTERMEDIATE_PREFIX + "assets\\"

ASSEMBLY_FOLDER = TL_PREFIX + "assembly\\"
ASSEMBLY_FOLDER_EDITING = INTERMEDIATE_PREFIX + "assembly\\"

TABLE_BACKUP_PREFIX = "patch_backup_"

class Connection():
    DB_PATH = None

    def __init__(self):
        self.conn = sqlite3.connect(self.DB_PATH)
    def __enter__(self):
        return self.conn, self.conn.cursor()
    def __exit__(self, type, value, traceback):
        self.conn.close()

class MDBConnection(Connection):
    DB_PATH = MDB_PATH

class MetaConnection(Connection):
    DB_PATH = META_PATH


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding='utf-8') as f:
            return json.load(f)
    raise FileNotFoundError(f"Json not found: {path}")


def save_json(path, data):
    with open(path, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def download_json(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

def xor_bytes(a, b):
    return (np.frombuffer(a, dtype='uint8') ^ np.frombuffer(b, dtype='uint8')).tobytes()

def fix_transparency(file_path, out_path=None):
    os.system(f"transparency-fix.exe {file_path}{f' {out_path}' if out_path else ''}")

def fix_transparency_pil(file_path, out_path):
    with Image.open(file_path) as image:
        tmp = image.copy()
        tmp = tmp.convert("RGBa")
        tmp = tmp.filter(ImageFilter.GaussianBlur(1))

        tmp.paste(image, mask=image.split()[3])
        tmp.putalpha(image.split()[3])
        tmp = tmp.convert("RGBA")
        tmp.save(out_path if out_path else file_path)


def test_for_type(args):
    path, type = args
    data = load_json(path)
    if data.get('type', None) == type:
        return (True, data)
    return (False, None)

def get_asset_and_type(path):
    data = load_json(path)
    return (data.get('type'), data)

def get_asset_path(asset_hash):
    return os.path.join(DATA_PATH, asset_hash[:2], asset_hash)

def strings_numeric_key(item):
    if item.isnumeric():
        return int(item)
    return item


def fetch_latest_github_release(username, repo):
    url = f'https://api.github.com/repos/{username}/{repo}/releases'
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    cur_version = None
    for version in data:
        if version['prerelease']:
            continue
        cur_version = version
        break

    if not cur_version:
        raise Exception("No release found")
    
    return cur_version


LATEST_DATA = None
def get_latest_json():
    global LATEST_DATA

    if not LATEST_DATA:
        LATEST_DATA = fetch_latest_github_release('KevinVG207', 'Uma-Carotene-TL')

    return LATEST_DATA

def download_file(url, path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            bar_format = TQDM_FORMAT + " {n_fmt}/{total_fmt}"
            progress_bar = tqdm(total=int(r.headers.get('Content-Length', 0)), unit='B', unit_scale=True, desc=f"Downloading", bar_format=bar_format)
            for chunk in r.iter_content(chunk_size=8192):
                progress_bar.update(len(chunk))
                f.write(chunk)

def download_latest():
    print("Downloading latest translation files")

    cur_version = get_latest_json()
    
    ver = cur_version['tag_name']
    
    dl_asset = None
    for asset in cur_version['assets']:
        if asset['name'].endswith(f"{ver}.zip"):
            dl_asset = asset
            break

    if not dl_asset:
        raise Exception("No translations zip found")
    
    print(f"Downloading {ver}")

    os.makedirs('tmp', exist_ok=True)
    dl_path = get_asset(os.path.join('tmp', dl_asset['name']))

    download_file(dl_asset['browser_download_url'], dl_path)

    final_path = get_relative(TL_PREFIX)
    if os.path.exists(final_path):
        print("Deleting old files")
        shutil.rmtree(final_path)
    os.makedirs(final_path, exist_ok=True)

    print("Extracting")

    with zipfile.ZipFile(dl_path, 'r') as zip_ref:
        zip_ref.extractall(final_path)
    
    shutil.rmtree('tmp')

    print("Done")

def clean_download():
    print("Removing temporary files")
    if os.path.exists(get_relative(TL_PREFIX)):
        shutil.rmtree(get_relative(TL_PREFIX))
    print("Done")

def tqdm(*args, **kwargs):
    if not kwargs.get('bar_format'):
        kwargs['bar_format'] = TQDM_FORMAT
    if not kwargs.get('ncols'):
        kwargs['ncols'] = TQDM_NCOLS
    return _tqdm.tqdm(*args, **kwargs)

def get_game_folder():
    with open(os.path.expandvars("%AppData%\dmmgameplayer5\dmmgame.cnf"), "r", encoding='utf-8') as f:
        game_data = json.loads(f.read())
    
    if not game_data or not game_data.get('contents'):
        return None
    
    path = None
    for game in game_data['contents']:
        if game.get('productId') == 'umamusume':
            path = game.get('detail', {}).get('path', None)
            break
    
    return path

APPLICATION = None
def run_widget(widget, *args, **kwargs):
    global APPLICATION

    if not APPLICATION:
        APPLICATION = QApplication([])
        APPLICATION.setWindowIcon(QIcon(get_asset('assets/icon.ico')))
    
    widget = widget(*args, **kwargs)
    widget.show()
    APPLICATION.exec_()
    return