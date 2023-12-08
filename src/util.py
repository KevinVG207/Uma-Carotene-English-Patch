import sqlite3
import os
import json
import requests
import numpy as np
import shutil
import zipfile
from PIL import Image, ImageFilter
import tqdm as _tqdm

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


config = load_json("config.json") if os.path.exists("config.json") else load_json("src/config.json")


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


LATEST_DATA = None
def get_latest_json():
    global LATEST_DATA

    if not LATEST_DATA:
        url = config['tl_source']  # api.github.com/.../releases
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
        
        LATEST_DATA = cur_version

    return LATEST_DATA


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
    dl_path = os.path.join('tmp', dl_asset['name'])

    with requests.get(dl_asset['browser_download_url'], stream=True) as r:
        r.raise_for_status()
        with open(dl_path, "wb") as f:
            bar_format = TQDM_FORMAT + " {n_fmt}/{total_fmt}"
            progress_bar = tqdm(total=int(r.headers.get('Content-Length', 0)), unit='B', unit_scale=True, desc=f"Downloading", bar_format=bar_format)
            for chunk in r.iter_content(chunk_size=8192):
                progress_bar.update(len(chunk))
                f.write(chunk)


    if os.path.exists(TL_PREFIX):
        print("Deleting old files")
        shutil.rmtree(TL_PREFIX)
    os.makedirs(TL_PREFIX, exist_ok=True)

    print("Extracting")

    with zipfile.ZipFile(dl_path, 'r') as zip_ref:
        zip_ref.extractall(TL_PREFIX)
    
    shutil.rmtree('tmp')

    print("Done")

def clean_download():
    print("Removing temporary files")
    if os.path.exists(TL_PREFIX):
        shutil.rmtree(TL_PREFIX)
    print("Done")

def tqdm(*args, **kwargs):
    if not kwargs.get('bar_format'):
        kwargs['bar_format'] = TQDM_FORMAT
    if not kwargs.get('ncols'):
        kwargs['ncols'] = TQDM_NCOLS
    return _tqdm.tqdm(*args, **kwargs)