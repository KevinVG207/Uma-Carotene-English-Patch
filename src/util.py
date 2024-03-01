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
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon
from fontTools.ttLib import TTFont
import win32gui
import win32process
import win32api
import win32con
import lz4.frame
import time
import glob
import pyphen
from functools import cache
from multiprocessing import Pool
import re
import hashlib

DLL_NAMES = ['version.dll', 'umpdc.dll', 'xinput1_3.dll']

hyphen_dict = pyphen.Pyphen(lang='en_US')

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


APP_DIR = os.path.expandvars("%AppData%\\Uma-Carotene\\")
os.makedirs(APP_DIR, exist_ok=True)

SETTINGS_PATH = APP_DIR + "patcher_settings.json"


TQDM_FORMAT = "{desc}: {percentage:3.0f}% |{bar}|"
TQDM_NCOLS = 65

MDB_PATH = os.path.expandvars("%userprofile%\\appdata\\locallow\\Cygames\\umamusume\\master\\master.mdb")
META_PATH = os.path.expandvars("%userprofile%\\appdata\\locallow\\Cygames\\umamusume\\meta")

DATA_PATH = os.path.expandvars("%userprofile%\\appdata\\locallow\\Cygames\\umamusume\\dat")

TMP_FOLDER = get_asset("tmp\\")

TL_PREFIX = get_asset("translations\\")
INTERMEDIATE_PREFIX = get_asset("editing\\")

MDB_FOLDER = TL_PREFIX + "mdb\\"
MDB_FOLDER_EDITING = INTERMEDIATE_PREFIX + "mdb\\"

def get_tl_mdb_jsons():
    mdb_jsons = glob.glob(MDB_FOLDER + "*.json")
    mdb_jsons += glob.glob(MDB_FOLDER + "**\\*.json")
    return mdb_jsons


ASSETS_FOLDER = TL_PREFIX + "assets\\"
ASSETS_FOLDER_EDITING = INTERMEDIATE_PREFIX + "assets\\"

FLASH_FOLDER = TL_PREFIX + "flash\\"
FLASH_FOLDER_EDITING = INTERMEDIATE_PREFIX + "flash\\"

ASSEMBLY_FOLDER = TL_PREFIX + "assembly\\"
ASSEMBLY_FOLDER_EDITING = INTERMEDIATE_PREFIX + "assembly\\"

DIFF_FOLDER = TL_PREFIX + "diff\\"

TABLE_PREFIX = '_carotene'
TABLE_BACKUP_PREFIX = TABLE_PREFIX + "_bak_"

DLL_BACKUP_SUFFIX = ".bak"

class Connection:
    DB_PATH = None

    def __init__(self):
        if not self.DB_PATH or not os.path.exists(self.DB_PATH):
            display_critical_message("No Database Found", "We couldn't find the game's database file.\n\nPlease make sure that you have finished the tutorial and the initial in-game download before running Carotene.\n\nIf you are still encoutering this issue please join our Discord server for direct help.")
            raise GameDatabaseNotFoundException(f"Game database {self.DB_PATH} not found.")
        else:
            self.conn = sqlite3.connect(self.DB_PATH)

    def __enter__(self):
            return self.conn, self.conn.cursor()

    def __exit__(self, type, value, traceback):
            self.conn.close()

class MDBConnection(Connection):
    DB_PATH = MDB_PATH

class MetaConnection(Connection):
    DB_PATH = META_PATH

class GameDatabaseNotFoundException(Exception):
    pass

class NotEnoughSpaceException(Exception):
    pass

def display_critical_message(title, text):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText(text)
    msg.setWindowTitle(title)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.button(QMessageBox.Ok).setText("Ok")
    msg.exec_()

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


def get_process_path(hwnd: int) -> str:
    # Get the process ID of the window
    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    # Open the process, and get the executable path
    proc_path = win32process.GetModuleFileNameEx(win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid), 0)
    return os.path.abspath(proc_path)


window_handle = None
def _get_window_exact(hwnd: int, query: str):
    global window_handle
    if win32gui.IsWindowVisible(hwnd):
        if win32gui.GetWindowText(hwnd) == query:
            window_handle = hwnd


def _get_window_lazy(hwnd: int, query: str):
    global window_handle
    if win32gui.IsWindowVisible(hwnd):
        if query.lower() in win32gui.GetWindowText(hwnd).lower():
            window_handle = hwnd


def _get_window_startswith(hwnd: int, query: str):
    global window_handle
    if win32gui.IsWindowVisible(hwnd):
        if win32gui.GetWindowText(hwnd).startswith(query):
            window_handle = hwnd

def _get_window_by_executable(hwnd: int, query: str):
    global window_handle
    if win32gui.IsWindowVisible(hwnd):
        proc_path = get_process_path(hwnd)
        executable = os.path.basename(proc_path)
        if executable == query:
            window_handle = hwnd


LAZY = _get_window_lazy
EXACT = _get_window_exact
STARTSWITH = _get_window_startswith
EXEC_MATCH = _get_window_by_executable

def get_window_handle(query: str, type=LAZY) -> str:
    global window_handle

    window_handle = None
    win32gui.EnumWindows(type, query)
    return window_handle

def check_umamusume():
    return get_window_handle("umamusume.exe", EXEC_MATCH)

def close_umamusume():
    if check_umamusume():
        # Messagebox telling the user to close the game, choose Cancel and Continue
        qm = QMessageBox()
        # qm.warning(qm, "Please close the game", "Please close the game before continuing.", QMessageBox.Cancel | QMessageBox.Ok, QMessageBox.Cancel)
        qm.setText("Please close the game before continuing.")
        qm.setWindowTitle("Please close the game")
        qm.setIcon(QMessageBox.Warning)
        qm.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
        qm.setDefaultButton(QMessageBox.Cancel)
        qm.setEscapeButton(QMessageBox.Cancel)
        run_widget(qm)
        if qm.clickedButton() == qm.Cancel:
            return False
        
        if check_umamusume():
            return False

    return True

def test_for_type(args):
    path, type = args
    data = load_json(path)
    if data.get('type', None) == type:
        return (True, data)
    return (False, None)

def get_asset_and_type(path):
    data = load_json(path)
    return (data.get('type'), data, path)

def get_asset_path(asset_hash):
    return os.path.join(DATA_PATH, asset_hash[:2], asset_hash)

def strings_numeric_key(item):
    if item.isnumeric():
        return int(item)
    return item


def fetch_latest_github_release(username, repo, prerelease=False):
    url = f'https://umapyoi.net/api/v1/github/{username}/{repo}/releases'
    try:
        r = requests.get(url)
        r.raise_for_status()
        if 200 <= r.status_code < 300:
            raise Exception("Umapyoi.net API request failed")
        data = r.json()
    except:
        # Fallback to github api
        url = f'https://api.github.com/repos/{username}/{repo}/releases'
        r = requests.get(url)
        r.raise_for_status()
        if not 200 <= r.status_code < 300:
            raise Exception("Github API request failed")
        data = r.json()
    cur_version = None
    for version in data:
        if version['prerelease'] and not prerelease:
            continue
        cur_version = version
        break

    if not cur_version:
        raise Exception("No release found")
    
    return cur_version


LATEST_DATA = None
def get_latest_json(prerelease=False):
    global LATEST_DATA

    if not LATEST_DATA:
        LATEST_DATA = fetch_latest_github_release('KevinVG207', 'Uma-Carotene-TL', prerelease)

    return LATEST_DATA

LATEST_DLL_DATA = None
def get_latest_dll_json(prerelease=False):
    global LATEST_DLL_DATA

    if not LATEST_DLL_DATA:
        LATEST_DLL_DATA = fetch_latest_github_release('KevinVG207', 'Uma-Carotenify', prerelease)

    return LATEST_DLL_DATA

def download_file(url, path, no_progress=False):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            bar_format = TQDM_FORMAT + " {n_fmt}/{total_fmt}"
            if no_progress:
                progress_bar = None
            else:
                progress_bar = tqdm(total=int(r.headers.get('Content-Length', 0)), unit='B', unit_scale=True, desc=f"Downloading", bar_format=bar_format)
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

                if progress_bar:
                    progress_bar.update(len(chunk))

def download_latest(ignore_filesize=False, prerelease=False):
    print("Downloading latest translation files")

    cur_version = get_latest_json(prerelease)
    
    ver = cur_version['tag_name']
    
    dl_asset = None
    for asset in cur_version['assets']:
        if asset['name'].endswith(f"{ver}.zip"):
            dl_asset = asset
            break

    if not dl_asset:
        raise Exception("No translations zip found")
    
    if not ignore_filesize:
        # Check if we have enough space
        enough, err = check_enough_space(int(dl_asset['size']))
        if not enough:
            raise NotEnoughSpaceException(err)
    
    print(f"Downloading {ver}")

    os.makedirs(TMP_FOLDER, exist_ok=True)
    dl_path = os.path.join(TMP_FOLDER, dl_asset['name'])

    download_file(dl_asset['browser_download_url'], dl_path)

    final_path = TL_PREFIX
    if os.path.exists(final_path):
        print("Deleting old files")
        shutil.rmtree(final_path)
    os.makedirs(final_path, exist_ok=True)

    print("Extracting")

    with zipfile.ZipFile(dl_path, 'r') as zip_ref:
        zip_ref.extractall(final_path)
    
    shutil.rmtree(TMP_FOLDER)

    # print("Done")
    return ver

def clean_download():
    print("Removing temporary files")
    if os.path.exists(TL_PREFIX):
        shutil.rmtree(TL_PREFIX)
    # print("Done")

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
def run_widget(widget, main=False, *args, **kwargs):
    global APPLICATION

    if not APPLICATION:
        APPLICATION = QApplication([])
        APPLICATION.setWindowIcon(QIcon(get_asset('assets/icon.ico')))
    
    if hasattr(widget, 'exec_') and not main:
        widget.exec_(*args, **kwargs)
        return
    widget = widget(*args, **kwargs)
    widget.show()
    APPLICATION.exec_()
    return

def download_lz4(url, mdb_path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        lz4_context = lz4.frame.create_decompression_context()
        with open(mdb_path, "wb") as f:
            bar_format = TQDM_FORMAT + " {n_fmt}/{total_fmt}"
            progress_bar = tqdm(total=int(r.headers.get('Content-Length', 0)), unit='B', unit_scale=True, desc=f"Downloading", bar_format=bar_format)
            for chunk in r.iter_content(chunk_size=4096):
                progress_bar.update(len(chunk))
                chunk, _, _ = lz4.frame.decompress_chunk(lz4_context, chunk)
                f.write(chunk)

def redownload_mdb():
    # Find the url of the latest mdb
    with MetaConnection() as (conn, cursor):
        cursor.execute("SELECT h FROM a WHERE n = 'master.mdb.lz4';")
        row = cursor.fetchone()
    
    if not row:
        raise Exception("master.mdb.lz4 not found in meta")
    
    asset_hash = row[0]

    # Backup the existing mdb
    mdb_path = MDB_PATH
    mdb_path_bak = f'{mdb_path}.{int(time.time())}.bak'
    shutil.copy(mdb_path, mdb_path_bak)

    # Download the mdb
    url = 'https://prd-storage-umamusume.akamaized.net/dl/resources/Generic/{0:.2}/{0}'.format(asset_hash)
    download_lz4(url, mdb_path)
    print("=== Downloaded latest master.mdb. You may now apply the patch again. ===")

def download_asset(hash, no_progress=False):
    asset_path = get_asset_path(hash)
    if os.path.exists(asset_path):
        return
    
    print_str = f"Downloading missing asset {hash}"
    if no_progress:
        print_str = "\n" + print_str
    
    print(print_str)

    os.makedirs(os.path.dirname(asset_path), exist_ok=True)

    url = 'https://prd-storage-umamusume.akamaized.net/dl/resources/Windows/assetbundles/{0:.2}/{0}'.format(hash)
    
    download_file(url, asset_path, no_progress=no_progress)

def prepare_font():
    with MetaConnection() as (conn, cursor):
        cursor.execute("SELECT h FROM a WHERE n = 'font/dynamic01.otf'")
        row = cursor.fetchone()
    
    if not row:
        raise Exception("Font not found in meta db.")

    font_hash = row[0]
    
    font_path = MDB_FOLDER_EDITING + "font/dynamic01.otf"
    os.makedirs(os.path.dirname(font_path), exist_ok=True)

    if not os.path.exists(font_path):
        shutil.copy(get_asset_path(font_hash), font_path)

    return TTFont(font_path)

@cache
def get_font_data(ttfont):
    t = ttfont.getBestCmap()
    s = ttfont.getGlyphSet()
    
    return t, s

@cache
def _get_char_width(char, ttfont):
    t, s = get_font_data(ttfont)
    a = ord(char)
    b = t[a]
    c = s[b]
    return c.width


def get_text_width(text, ttfont, scale=1.0):
    tot = 0
    for char in text:
        try:
            tot += _get_char_width(char, ttfont) * scale
        except KeyError:
            # Char not found in font
            pass

    return tot

def wrap_text_to_width(text, width, ttfont, scale=1.0, hyphen=True):
    global hyphen_dict

    words = text.split(" ")
    lines = []
    cur_line = ""
    for word in words:
        tmp_line = cur_line + " " + word if cur_line else word

        if get_text_width(tmp_line, ttfont, scale) <= width:
            cur_line = tmp_line
        else:
            if not hyphen:
                lines.append(cur_line)
                cur_line = word
                continue

            # Try to hyphenate
            hyphenations = list(hyphen_dict.iterate(word))
            if not hyphenations:
                lines.append(cur_line)
                cur_line = word
            else:
                hyphenated = False
                for hyphenation in hyphenations:

                    # Skip 1-2 letter hyphenations
                    if any(len(h) <= 2 for h in hyphenation):
                        continue

                    tmp_line = cur_line + " " + hyphenation[0] + "-" if cur_line else hyphenation[0] + "-"
                    if get_text_width(tmp_line, ttfont, scale) <= width:
                        lines.append(tmp_line)
                        cur_line = hyphenation[1]
                        hyphenated = True
                        break
                if not hyphenated:
                    lines.append(cur_line)
                    cur_line = word

    if cur_line:
        lines.append(cur_line)

    return "\n".join(lines)

def split_mdb_path(path):
    rel_path = os.path.relpath(path, MDB_FOLDER)
    path_segments = os.path.normpath(rel_path).rsplit(".", 1)[0].split(os.sep)
    return tuple(path_segments)

def add_period(text):
    if not text.endswith('.') and not text.endswith('.)'):
        text += '.'
    return text

def add_nested_dict(d, path, value):
    for key in path[:-1]:
        if key not in d:
            d[key] = {}
        d = d[key]
    d[path[-1]] = value

def get_assets_type_dict():
    jsons = glob.glob(ASSETS_FOLDER + "\\**\\*.json", recursive=True)
    jsons += glob.glob(FLASH_FOLDER + "\\**\\*.json", recursive=True)

    with Pool() as pool:
        results = list(tqdm(pool.imap_unordered(get_asset_and_type, jsons, chunksize=128), total=len(jsons), desc="Looking for assets"))

    # asset_dict = {result[0]: result[1] for result in results if result[0]}
    asset_dict = {}

    for result in results:
        asset_type, asset_data, path = result
        if not asset_type:
            continue

        if asset_type not in asset_dict:
            asset_dict[asset_type] = []

        asset_dict[asset_type].append((asset_data, path))

    return asset_dict

def filter_tags(in_str):
    # Remove any <> tags from string.
    return re.sub(r'<[^>]*>', '', in_str)

def remove_size_tags(str):
    # Remove any <size=?> or </size> tags from string.
    return re.sub(r"<size=[^>]*>|</size>", "", str)

def process_colored_text(in_str):
    color_list = []
    used_text = set()

    matches = re.findall(r"<col=[^>]*>.*?</col>", in_str)

    for match_str in matches:
        color_id = re.search(r"<col=([^>]*)>", match_str).group(1)
        text = re.search(r"<col=[^>]*>(.*)</col>", match_str).group(1)

        # Skip if text has already been colored.
        if text in used_text:
            continue

        used_text.add(text)

        color_list.append({
            "text": text,
            "color_id": int(color_id)
        })
    
    # Remove all <col=?> and </col> tags from string.
    in_str = re.sub(r"<col=[^>]*>|</col>", "", in_str)

    return in_str, color_list

def apply_colored_text(in_str, color_list):
    if not color_list:
        return in_str

    for color_info in color_list:
        match_str = color_info.get('Text') or color_info.get('text')
        color_id = color_info.get('FontColor') or color_info.get('color_id')

        if not match_str or not color_id:
            raise Exception(f"Invalid color info {color_info}")

        in_str = in_str.replace(match_str, f"<col={color_id}>{match_str}</col>")

    return in_str

def make_diff(edited_bytes, source_bytes):
    hasher = hashlib.sha256()
    hasher.update(edited_bytes)
    edited_hash = hasher.digest()

    hasher = hashlib.sha256()
    hasher.update(source_bytes)
    source_hash = hasher.digest()

    max_len = max(len(edited_bytes), len(source_bytes))

    gen = np.random.default_rng(seed=int(edited_hash.hex(), 16))
    edited_bytes += gen.bytes(max_len - len(edited_bytes))
    gen = np.random.default_rng(seed=int(source_hash.hex(), 16))
    source_bytes += gen.bytes(max_len - len(source_bytes))

    diff = xor_bytes(edited_bytes, source_bytes)

    return diff

def apply_diff(source_bytes, diff):
    if len(diff) < len(source_bytes):
        raise Exception("Diff is smaller than source")
    
    delta_len = len(diff) - len(source_bytes)

    if delta_len > 0:
        hasher = hashlib.sha256()
        hasher.update(source_bytes)
        source_hash = hasher.digest()

        gen = np.random.default_rng(seed=int(source_hash.hex(), 16))
        source_bytes += gen.bytes(delta_len)

    return xor_bytes(source_bytes, diff)

def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()

def write_bytes(data, path):
    with open(path, "wb") as f:
        f.write(data)

def _check_enough_space(path, needed):
    free_space = shutil.disk_usage(path).free

    if free_space < needed:
        return False, (path, needed, free_space)
    
    return True, None

def check_enough_space(size):
    app_folder = os.path.realpath(APP_DIR)
    game_folder = os.path.realpath(DATA_PATH)

    # Extract the windows drive letters.
    app_drive = os.path.splitdrive(app_folder)[0]
    game_drive = os.path.splitdrive(game_folder)[0]

    failures = []

    if app_drive == game_drive:
        # Only check once.
        needed = 2 * size
        enough, err = _check_enough_space(app_drive, needed)
        if not enough:
            failures.append(err)
    
    else:
        # app_drive needs 2x size
        needed = 2 * size
        enough, err = _check_enough_space(app_drive, needed)
        if not enough:
            failures.append(err)

        enough, err = _check_enough_space(game_drive, size)
        if not enough:
            failures.append(err)
    
    if failures:
        err_list = []
        err_list.append("There may not be enough space on the following drives:<br>")

        for err in failures:
            err_list.append(f"{err[0]} {err[1] / 1024**3:.2f} GB needed, {err[2] / 1024**3:.2f} GB available")

        err_list.append("<br>These are estimations, so you may still try to install.<br>Click the Patch/Update button again to force the patch.")

        return False, "<br>".join(err_list)
    
    return True, None

def running_from_game_folder():
    return os.path.abspath(os.getcwd()) == os.path.abspath(get_game_folder())

def send_umalauncher_signal(endpoint, data={}):
    # Send signals to Uma Launcher about the state of the patcher.
    ul_domain = "http://127.0.0.1:3150/"
    url = ul_domain + endpoint
    try:
        requests.post(url, json=data, verify=False, timeout=1)
    except:
        pass

def send_start_signal():
    send_umalauncher_signal("patcher-start")

def send_finish_signal():
    send_umalauncher_signal("patcher-finish", {"success": True})

def send_error_signal(error_string):
    send_umalauncher_signal("patcher-finish", {"success": False, "error": error_string})