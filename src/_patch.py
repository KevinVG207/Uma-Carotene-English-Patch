import util
import os
import glob
import shutil
import io
import version
import unity
from UnityPy.enums import TextureFormat
from sqlite3 import Error as SqliteError
from PIL import Image, ImageFile
from settings import settings, pc, filter_mdb_jsons
import math
import json
import re

ImageFile.LOAD_TRUNCATED_IMAGES = True

FONT = None

# def backup_mdb():
#     print("Backing up MDB...")
#     shutil.copy(util.MDB_PATH, util.MDB_PATH + f".{round(time.time())}")


def mark_mdb_translated(ver=None):
    mark_mdb_untranslated()

    if not ver:
        ver = version.version_to_string(version.VERSION)

    settings.installed_version = ver

    print("Creating table")
    with util.MDBConnection() as (conn, cursor):
        cursor.execute("CREATE TABLE carotene (version TEXT);")

        # Mark as translated
        cursor.execute(
            "INSERT INTO carotene (version) VALUES (?);",
            (ver,)
        )
        conn.commit()

    print("Marking complete.")


def mark_mdb_untranslated():
    settings.installed_version = None

    print("Dropping table")
    with util.MDBConnection() as (conn, cursor):
        # Remove carotene table if it exists
        cursor.execute("DROP TABLE IF EXISTS carotene;")
        conn.commit()

def _get_value_from_table(key):
    value = None
    with util.MDBConnection() as (conn, cursor):
        # Determine if carotene table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='carotene';")
        if not cursor.fetchone():
            return value

        # Get version
        cursor.execute(f"SELECT {key} FROM carotene;")
        row = cursor.fetchone()
        if not row:
            return value
        
        value = row[0]
    
    return value

def _set_value_in_table(key, value):
    with util.MDBConnection() as (conn, cursor):
        # Determine if carotene table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='carotene';")
        if not cursor.fetchone():
            return

        # Get version
        cursor.execute(f"UPDATE carotene SET {key} = ?;", (value,))
        conn.commit()

def _get_version_from_table():
    return _get_value_from_table("version")

def _is_meta_updated():
    if not _is_meta_patched():
        return False

    cur_hashes = set()
    bak_hashes = set()

    with util.MetaConnection() as (conn, cursor):
        cursor.execute("SELECT h from a;")
        cur_hashes = set([row[0] for row in cursor.fetchall()])

    with util.MetaBackupConnection() as (conn, cursor):
        cursor.execute("SELECT h from a;")
        bak_hashes = set([row[0] for row in cursor.fetchall()])

    if cur_hashes != bak_hashes:
        return True

    return False

def _is_meta_patched():
    bak_path = util.META_PATH + util.META_BACKUP_SUFFIX

    if not os.path.exists(bak_path):
        return False
    
    return True


def get_current_patch_ver():
    # Load settings
    cur_patch_ver = settings.installed_version
    cur_dll_ver = settings.dll_version
    install_started = settings.install_started
    is_installed = settings.installed
    dll_name = settings.dll_name

    if not dll_name:
        dll_path = None
    else:
        dll_path = os.path.join(util.get_game_folder(), dll_name)

    mdb_ver = _get_version_from_table()

    meta_is_patched = _is_meta_patched()
    meta_is_updated = _is_meta_updated()

    if install_started:
        # The patcher was started, but not finished.
        return "unfinished", None

    # Not installed
    if not is_installed:
        if mdb_ver:
            # The mdb is marked as translated, but the patch was not installed.
            return "partial", None

        # Nothing is installed
        return None, None
    
    # Installed
    if not mdb_ver:
        # The mdb is not marked as translated, but the patch was installed.
        # The game has been updated.
        return "partial", None
    
    if not dll_path:
        # This should not happen.
        return "partial", None

    if not os.path.exists(dll_path):
        # The dll is not installed, but the mdb is marked as translated.
        # The dll was deleted.
        return "dllnotfound", None

    if not mdb_ver or not cur_dll_ver:
        # The mdb is not marked as translated, or the dll was never installed.
        return "partial", None

    if cur_patch_ver != mdb_ver:
        # The mdb version does not match the installed patch version.
        # This should never happen, but we mark it as partial just in case.
        return "partial", None
    
    if not meta_is_patched:
        # The meta DB is no longer patched.
        return "partial", None
    
    if meta_is_updated:
        # The meta DB has been updated.
        return "partial", None
    
    # The patch is installed.
    return cur_patch_ver, cur_dll_ver


def import_mdb():
    mdb_jsons = util.get_tl_mdb_jsons()
    mdb_jsons = filter_mdb_jsons(mdb_jsons)

    with util.MDBConnection() as (conn, cursor):
        for mdb_json in util.tqdm(mdb_jsons, desc="Importing MDB"):
            key = util.split_mdb_path(mdb_json)
            table = key[0]

            # Backup the table
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {util.TABLE_BACKUP_PREFIX}{table} AS SELECT * FROM {table};")

            # print(f"Importing {table} {category}")
            data = util.load_json(mdb_json)

            for index, entry in data.items():
                text = None
                if entry.get('processed'):
                    text = entry['processed']
                elif entry.get('text'):
                    text = entry['text']
                
                if not text:
                    print(f"Skipping {table} {index} - No text found")
                    continue

                ## Vars that can be used:
                # text
                # table
                # key (Holds table and subcategories)
                # index
                
                match table:
                    # TODO: Implement other tables
                    case "text_data":
                        category = key[1]
                        cursor.execute(
                            f"""UPDATE {table} SET text = ? WHERE category = ? and `index` = ?;""",
                            (text, category, index)
                        )
                    case "race_jikkyo_message":
                        cursor.execute(
                            f"""UPDATE {table} SET message = ? WHERE id = ?;""",
                            (text, index)
                        )

        conn.commit()
        cursor.execute("VACUUM;")
        conn.commit()

    print("Import complete.")


def revert_meta_db():
    print("Reverting meta DB")

    if not _is_meta_patched():
        return
    
    meta_is_updated = _is_meta_updated()

    if not meta_is_updated:
        shutil.copy(util.META_PATH + util.META_BACKUP_SUFFIX, util.META_PATH)
    
    os.remove(util.META_PATH + util.META_BACKUP_SUFFIX)

def backup_meta_db():
    print("Backing up meta DB")
    shutil.copy(util.META_PATH, util.META_PATH + util.META_BACKUP_SUFFIX)


def clean_asset_backups():
    asset_backups = glob.glob(util.DATA_PATH + "\\**\\*.bak", recursive=True)
    print(f"Amount of backups to revert: {len(asset_backups)}")
    for asset_backup in asset_backups:
        asset_path = asset_backup.rsplit(".", 1)[0]
        if not os.path.exists(asset_path):
            print(f"Deleting {asset_backup}")
            os.remove(asset_backup)
        else:
            shutil.move(asset_backup, asset_path)
    # print("Done")

def create_new_image_from_path_id(asset_bundle, path_id, diff_path):
    # Read the original texture
    texture_object = asset_bundle.assets[0].files[path_id]
    texture_read = texture_object.read()
    source_bytes_buffer = io.BytesIO()
    texture_read.image.save(source_bytes_buffer, format="PNG")
    source_bytes_buffer.seek(0)
    source_bytes = source_bytes_buffer.read()
    source_bytes_buffer.close()

    # Read the diff texture
    with open(diff_path, "rb") as f:
        diff_bytes = f.read()
    
    # Apply the diff
    new_bytes = util.apply_diff(source_bytes, diff_bytes)
    # max_len = max(len(diff_bytes), len(source_bytes))

    # diff_bytes = diff_bytes.ljust(max_len, b'\x00')
    # source_bytes = source_bytes.ljust(max_len, b'\x00')

    # new_bytes = util.xor_bytes(diff_bytes, source_bytes)

    return new_bytes, texture_read

def set_group_0(metadatas):
    # Change asset group so it doesn't get deleted.
    with util.MetaConnection() as (conn, cursor):
        # Change group to 0 if it's currently 1.
        for metadata in metadatas:
            asset_hash = metadata['hash']
            cursor.execute("UPDATE a SET g = 0 WHERE h = ? AND g = 1;", (asset_hash,))
        conn.commit()

def handle_backup(asset_hash, force=False):
    asset_path = util.get_asset_path(asset_hash)
    asset_path_bak = asset_path + ".bak"

    if not os.path.exists(asset_path):
        # Try to download the missing asset
        row = None
        with util.MetaConnection() as (conn, cursor):
            cursor.execute("SELECT i FROM a WHERE h = ?;", (asset_hash,))
            row = cursor.fetchone()

        if not row:
            print(f"Asset not found: {asset_hash} - Skipping")
            return None

        # Download the asset
        # print(f"\nAsset {asset_hash} not found. Downloading.")
        util.download_asset(asset_hash, no_progress=True)

    if not os.path.exists(asset_path_bak):
        shutil.copy(asset_path, asset_path_bak)
    elif force:
        shutil.copy(asset_path_bak, asset_path)

    return asset_path

def _import_texture(asset_metadata):
    hash = asset_metadata['hash']
    asset_path = handle_backup(hash)

    if not asset_path:
        return
    
    # print(f"Replacing {os.path.basename(asset_path)}")
    asset_bundle, _ = unity.load_assetbundle(asset_path, hash)
    
    for texture_data in asset_metadata['textures']:
        path_id = texture_data['path_id']
        diff_path = os.path.join(util.ASSETS_FOLDER, asset_metadata['file_name'], texture_data['name'] + ".diff")

        new_bytes, texture_read = create_new_image_from_path_id(asset_bundle, path_id, diff_path)

        # Create new image
        new_image_buffer = io.BytesIO()
        new_image_buffer.write(new_bytes)
        new_image_buffer.seek(0)
        new_image = Image.open(new_image_buffer)

        # Replace the image
        texture_read.m_TextureFormat = TextureFormat.BC7
        texture_read.image = new_image
        texture_read.save()

        new_image_buffer.close()
    
    with open(asset_path, "wb") as f:
        f.write(asset_bundle.file.save(packer="original"))

def import_textures(texture_asset_metadatas):
    print(f"Replacing {len(texture_asset_metadatas)} textures.")
    texture_asset_metadatas = [a[0] for a in texture_asset_metadatas]

    with util.UmaPool() as pool:
        _ = list(util.tqdm(pool.imap_unordered(_import_texture, texture_asset_metadatas, chunksize=16), total=len(texture_asset_metadatas), desc="Importing textures"))


def _import_flash(flash_metadata):
    hash = flash_metadata['hash']
    asset_path = handle_backup(hash)

    if not asset_path:
        return
    
    asset_bundle, _ = unity.load_assetbundle(asset_path, hash)

    for path_id, mpl_dict in flash_metadata['data'].items():
        obj = asset_bundle.assets[0].files[int(path_id)]
        tree = obj.read_typetree()

        for mpl_id, tpl_dict in mpl_dict.items():
            for tpl_name, tp_data in tpl_dict.items():
                # Find textparameter data.
                for mp_data in tree['_motionParameterGroup']['_motionParameterList']:
                    if mp_data['_id'] == mpl_id:
                        for tp_dict in mp_data['_textParamList']:
                            if tp_dict['_objectName'] == tpl_name:
                                # Replace textparameter data.
                                tp_dict.update(tp_data)
                                break
                        break
        
        obj.save_typetree(tree)

    with open(asset_path, "wb") as f:
        f.write(asset_bundle.file.save(packer="original"))


def import_flash(flash_metadatas):
    print(f"Replacing {len(flash_metadatas)} flash files.")
    flash_metadatas = [a[0] for a in flash_metadatas]

    for flash_metadata in util.tqdm(flash_metadatas, desc="Import. flash TLs"):
        _import_flash(flash_metadata)

def set_clip_length(root, clip_asset_path_id, length_diff):
    clip_asset = root.assets_file.files[clip_asset_path_id]
    clip_tree = clip_asset.read_typetree()
    clip_tree['ClipLength'] += length_diff
    clip_asset.save_typetree(clip_tree)


def _import_story(story_data):
    hash = story_data['hash']
    bundle_path = handle_backup(hash, force=True)

    if not bundle_path:
        print(f"\nStory not found: {story_data['file_name']} {hash} - Skipping")
        return
    # print(f"Importing {os.path.basename(bundle_path)}")

    asset_bundle, root = unity.load_assetbundle(bundle_path, hash)

    tree = root.read_typetree()

    file_name = story_data['file_name']

    if file_name.startswith("race/"):
        raise NotImplementedError("Race stories(?) not implemented yet.")
    
    tree['Title'] = story_data['title']
    # org_typewritespeed = tree['TypewriteCountPerSecond']
    tree['TypewriteCountPerSecond'] *= 3

    for new_clip in story_data['data']:
        block_data = tree['BlockList'][new_clip['block_id']]
        text_clip = root.assets_file.files[new_clip['path_id']]
        text_clip_data = text_clip.read_typetree()

        if not text_clip_data['Text']:
            # Skip untranslated blocks.
            continue

        text_clip_data['Text'] = new_clip.get('processed') or new_clip['text']
        text_clip_data['Name'] = new_clip.get('name_processed') or new_clip['name']

        # Handle colored text.
        if new_clip.get('color_list') and text_clip_data.get('ColorTextInfoList'):
            new_color_list = []
            for color_info in new_clip['color_list']:
                new_color_list.append({
                    'Text': color_info['text'],
                    'FontColor': int(color_info['color_id']),
                })
            text_clip_data['ColorTextInfoList'] = new_color_list
        
        if new_clip.get('choices'):
            for i, choice in enumerate(text_clip_data['ChoiceDataList']):
                choice_data = new_clip['choices'][i]
                choice['Text'] = choice_data.get('processed') or choice_data['text']
        
        org_clip_length = text_clip_data['ClipLength']
        new_clip_length = new_clip['clip_length']

        if org_clip_length == new_clip_length:
            no_tags_text = [c for c in re.sub(r'<[^>]*>', '', new_clip['text']) if c.isalnum() or c.isspace()]
            txt_len = len(no_tags_text) * 1.5
            new_clip_length = int(text_clip_data['WaitFrame'] + max(txt_len, text_clip_data['VoiceLength']))
        
        if new_clip_length > org_clip_length:
            text_clip_data['ClipLength'] = new_clip_length
            old_block_length = block_data['BlockLength']
            new_block_length = new_clip_length + text_clip_data['StartFrame'] + 1
            block_data['BlockLength'] = new_block_length

            # Adjust anim lengths
            for track in block_data['CharacterTrackList']:
                for track_type, track_data in track.items():
                    if not track_type.endswith('MotionTrackData'):
                        continue
                    if not track_data['ClipList']:
                        continue
                    clip_path_id = track_data['ClipList'][-1]['m_PathID']
                    clip_asset = root.assets_file.files[clip_path_id]
                    clip_tree = clip_asset.read_typetree()
                    tmp_clip_length = clip_tree['ClipLength'] + new_clip_length - org_clip_length
                    clip_tree['ClipLength'] = tmp_clip_length
                    clip_asset.save_typetree(clip_tree)
            
            # Screen effects
            for track in block_data['ScreenEffectTrackList']:
                if not track['ClipList']:
                    continue
                clip_path_id = track['ClipList'][-1]['m_PathID']
                clip_asset = root.assets_file.files[clip_path_id]
                clip_tree = clip_asset.read_typetree()

                if clip_tree['StartFrame'] + clip_tree['ClipLength'] < old_block_length:
                    continue

                tmp_clip_length = clip_tree['ClipLength'] + new_clip_length - org_clip_length
                clip_tree['ClipLength'] = tmp_clip_length
                clip_asset.save_typetree(clip_tree)

        text_clip.save_typetree(text_clip_data)

    tree['Length'] = sum([block_data['BlockLength'] for block_data in tree['BlockList']])
    root.save_typetree(tree)

    with open(bundle_path, "wb") as f:
        f.write(asset_bundle.file.save(packer="original"))
    
    # Handle ruby text.
    ruby_file_name = file_name.replace("storytimeline", "ast_ruby").replace("hometimeline_", "ast_ruby_hometimeline_")
    with util.MetaConnection() as (conn, cursor):
        cursor.execute("SELECT h FROM a WHERE n = ?;", (ruby_file_name,))
        ruby_hash = cursor.fetchone()
    
    if not ruby_hash:
        # No ruby asset for this story.
        return

    ruby_path = handle_backup(ruby_hash[0])
    ruby_bundle, _ = unity.load_assetbundle(ruby_path, ruby_hash[0])

    for obj in ruby_bundle.assets[0].objects.values():
        tree = obj.read_typetree()
        if not tree.get('DataArray'):
            continue
        tree['DataArray'] = []
        obj.save_typetree(tree)

    with open(ruby_path, "wb") as f:
        f.write(ruby_bundle.file.save(packer="original"))


def import_stories(story_datas):
    #TODO: Increase chunk size (maybe 16?) when more stories are added.
    story_datas = [a[0] for a in story_datas]
    with util.UmaPool() as pool:
        _ = list(util.tqdm(pool.imap_unordered(_import_story, story_datas, chunksize=8), total=len(story_datas), desc="Importing stories"))

    # print(f"Replacing {len(story_datas)} stories.")
    # for story_data in story_datas:
    #     _import_story(story_data)


def _import_xor(xor_data):
    asset_path = handle_backup(xor_data['hash'], force=True)

    if not asset_path:
        return
    
    diff_path = os.path.join(util.ASSETS_FOLDER, xor_data['file_name'] + ".diff")

    if not os.path.exists(diff_path):
        print(f"Diff not found in TL files: {diff_path} - Skipping")
        return

    with open(diff_path, "rb") as f:
        diff_bytes = f.read()

    with open(asset_path, "rb") as f:
        source_bytes = f.read()

    new_bytes = util.apply_diff(source_bytes, diff_bytes)

    with open(asset_path, "wb") as f:
        f.write(new_bytes)


def import_movies(movie_metadatas):
    movie_datas = [a[0] for a in movie_metadatas]

    set_group_0(movie_datas)

    with util.UmaPool() as pool:
        _ = list(util.tqdm(pool.imap_unordered(_import_xor, movie_datas, chunksize=16), total=len(movie_datas), desc="Patching videos"))

    # print(f"Replacing {len(xor_datas)} xor files.")
    # for xor_data in xor_datas:
    #     _import_xor(xor_data)

def import_assets():
    clean_asset_backups()
    revert_meta_db()
    backup_meta_db()

    if not pc("flash") and not pc("textures") and not pc("story") and not pc("videos"):
        print("Skipping assets.")
        return

    asset_dict = util.get_assets_type_dict()

    if pc("flash"):
        import_flash(asset_dict.get('flash', []))
    if pc("textures"):
        import_textures(asset_dict.get('texture', []))
    if pc("story"):
        import_stories(asset_dict.get('story', []))
    if pc("videos"):
        import_movies(asset_dict.get('movie', []))


def _import_jpdict():
    jpdict_path = os.path.join(util.ASSEMBLY_FOLDER, "JPDict.json")

    if not os.path.exists(jpdict_path):
        print(f"JPDict not found: {jpdict_path} - Skipping")
        return

    jpdict = util.load_json(jpdict_path)

    lines = []

    for text_id, text_data in jpdict.items():
        if not text_data['text']:
            continue

        text = text_data['text'].replace("\r", "\\r").replace("\n", "\\n").replace("\"", "\\\"")
        lines.append(f"{text_id}\t{text}")

    return lines


def _import_hashed():
    hashed_path = os.path.join(util.ASSEMBLY_FOLDER, "hashed.json")

    if not os.path.exists(hashed_path):
        print(f"hashed.json not found: {hashed_path} - Skipping")
        return
    
    hashed = util.load_json(hashed_path)

    lines = []

    for text_data in hashed:
        lines.append(f"{text_data['hash']}\t{text_data['text']}")
    
    return lines


def check_tlg(config_path):
    base_path = os.path.dirname(config_path)
    paths = [
        'version.dll',
        'uxtheme.dll',
        'xinput1_3.dll',
        'umpdc.dll'
    ]
    paths = [os.path.join(base_path, p) for p in paths]
    if not os.path.exists(config_path):
        return None
    
    try:
        config = util.load_json(config_path)
        if 'maxFps' in config:
            dll_path = None
            for p in paths:
                if os.path.exists(p):
                    dll_path = p
                    break

            if dll_path:
                with open(dll_path, "rb") as f:
                    data = f.read()
                    if b"Trainer's Legend G" in data:
                        return os.path.basename(dll_path)
    except:
        return None
    
    return None


def cellar_exists(path: str) -> bool:
    if not os.path.exists(path):
        return False

    data = r""
    with open(path, "rb") as f:
        data = f.read()
    
    if b"cellar::windows" in data:
        return True

    return False


def fix_tlg_config(config_path):
    tlg_data = util.load_json(config_path)
    if not 'loadDll' in tlg_data:
        tlg_data['loadDll'] = []
    
    if 'carotene.dll' in tlg_data['loadDll']:
        tlg_data['loadDll'].remove('carotene.dll')
    
    if 'carrotjuicer.dll' in tlg_data['loadDll']:
        tlg_data['loadDll'].remove('carrotjuicer.dll')
    
    # Disable TLG text/asset replacement
    if 'replaceFont' in tlg_data:
        tlg_data['replaceFont'] = False
    if 'extraAssetBundlePaths' in tlg_data:
        tlg_data['extraAssetBundlePaths'] = []
    if 'replaceAssets' in tlg_data:
        tlg_data['replaceAssets'] = False
    if 'dicts' in tlg_data:
        tlg_data['dicts'] = []
    if 'static_dict' in tlg_data:
        tlg_data['static_dict'] = ""
    if 'stories_path' in tlg_data:
        tlg_data['stories_path'] = ""
    if 'text_data_dict' in tlg_data:
        tlg_data['text_data_dict'] = ""
    if 'character_system_text_dict' in tlg_data:
        tlg_data['character_system_text_dict'] = ""
    if 'race_jikkyo_comment_dict' in tlg_data:
        tlg_data['race_jikkyo_comment_dict'] = ""
    if 'race_jikkyo_message_dict' in tlg_data:
        tlg_data['race_jikkyo_message_dict'] = ""

    with open(config_path, "w") as f:
        json.dump(tlg_data, f, indent=4)


def import_assembly():
    print("Importing assembly text...")

    game_folder = util.get_game_folder()

    if not game_folder:
        raise ValueError("Game folder could not be determined.")
    
    if not os.path.exists(game_folder):
        raise FileNotFoundError(f"Game folder does not exist: {game_folder}.")

    lines = []
    lines += _import_jpdict()
    lines += _import_hashed()

    if not lines:
        print("No lines to import.")
        return

    translations_path = os.path.join(game_folder, "translations.txt")

    with open(translations_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"Imported {len(lines)} lines.")

    # print("Done.")

def download_dll(dl_latest=False, dll_name='version.dll'):
    if not dl_latest:
        print("Not downloading latest dll.")
        return

    game_folder = util.get_game_folder()

    if not game_folder:
        raise ValueError("Game folder could not be determined.")
    
    if not os.path.exists(game_folder):
        raise FileNotFoundError(f"Game folder does not exist: {game_folder}.")


    print("Looking for latest mod version")
    latest_data = util.get_latest_dll_json(settings.prerelease)
    print("Downloading patcher mod.")

    dll_url = None
    for asset in latest_data['assets']:
        if asset['name'] == 'version.dll':
            dll_url = asset['browser_download_url']
            break
    
    if not dll_url:
        raise Exception("version.dll not found in release assets.")
    
    prev_name = settings.dll_name
    if prev_name:
        prev_bak = prev_name + util.DLL_BACKUP_SUFFIX

        prev_path = os.path.join(game_folder, prev_name)
        prev_bak_path = os.path.join(game_folder, prev_bak)

        if os.path.exists(prev_path):
            print(f"Deleting {prev_name}")
            os.remove(prev_path)
        
        if os.path.exists(prev_bak_path):
            print(f"Reverting existing {prev_bak}")
            shutil.move(prev_bak_path, prev_path)
    

    # Check for tlg
    tlg_config_path = os.path.join(game_folder, "config.json")
    tlg_dll_name = check_tlg(tlg_config_path)
    if tlg_dll_name:
        print("TLG detected.")
        # dll_name = "carotene.dll"

        config_bak_path = tlg_config_path + util.DLL_BACKUP_SUFFIX
        if not os.path.exists(config_bak_path):
            print("Backing up existing config.json")
            shutil.copy(tlg_config_path, config_bak_path)
        else:
            print("Reverting existing config.json before patching.")
            shutil.copy(config_bak_path, tlg_config_path)
        settings.tlg_config_bak = os.path.basename(config_bak_path)

        fix_tlg_config(tlg_config_path)

        # Rename the dll
        tlg_dll_path = os.path.join(game_folder, tlg_dll_name)
        tlg_new_path = os.path.join(game_folder, 'tlg.dll')

        if os.path.exists(tlg_dll_path):
            print(f"Renaming {tlg_dll_name} to tlg.dll")
            shutil.move(tlg_dll_path, tlg_new_path)
        
        settings.tlg_orig_name = tlg_dll_name

    else:
        print("TLG not detected/does not need to be moved.")
    

    # Check for Cellar
    cellar_path = os.path.join(game_folder, "dxgi.dll")

    if not cellar_exists(cellar_path):
        # Download cellar
        if os.path.exists(cellar_path):
            # Backup what is there
            print("Backing up existing dxgi.dll")
            shutil.move(cellar_path, cellar_path + util.DLL_BACKUP_SUFFIX)
            settings.dxgi_backup = True
        
        print("Downloading Cellar.")
        util.download_file(util.CELLAR_URL, cellar_path)
        settings.cellar_downloaded = True
    else:
        print("Cellar detected. Skipping download.")


    dll_path = os.path.join(game_folder, dll_name)
    bak_path = dll_path + util.DLL_BACKUP_SUFFIX

    if os.path.exists(dll_path) and not os.path.exists(bak_path):
        print(f"Backing up existing {dll_name}")
        shutil.move(dll_path, bak_path)
    
    settings.dll_name = dll_name
    print("Downloading Carotenify")
    util.download_file(dll_url, dll_path)
    settings.dll_version = latest_data['tag_name']

def upgrade():
    prev_client = settings.client_version
    if not prev_client:
        return

    prev_client = tuple(prev_client)
    cur_client = version.VERSION

    # print(prev_client)
    # print(cur_client)

    print("Checking for upgrade...")

    if prev_client == cur_client:
        return
    
    if prev_client is None:
        # Either first time running, or < v0.1.4
        # Either way, try renaming tables.
        print("Upgrading from < v0.1.4 or first time running.\nRenaming existing tables.")

        with util.MDBConnection() as (conn, cursor):
            # Find table 'carotene'
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='carotene';")
            if cursor.fetchone():
                # Rename to new table name
                new_table = util.TABLE_PREFIX
                
                # Check if new table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (new_table,))
                if cursor.fetchone():
                    # Table already exists.
                    # Remove the old table.
                    cursor.execute("DROP TABLE carotene;")
                else:
                    cursor.execute(f"ALTER TABLE carotene RENAME TO {new_table};")
            
            # Find any that start with 'patch_backup_'
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'patch_backup_%';")
            tables = cursor.fetchall()
            if tables:
                for table in tables:
                    table = table[0]
                    new_table = util.TABLE_BACKUP_PREFIX + table[len('patch_backup_'):]

                    # Check if new table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (new_table,))
                    if cursor.fetchone():
                        # Table already exists.
                        # Remove the old table.
                        cursor.execute(f"DROP TABLE {new_table};")
                    else:
                        # Rename to new table name
                        cursor.execute(f"ALTER TABLE {table} RENAME TO {new_table};")

            conn.commit()
    
    if prev_client <= (0, 1, 9):
        # Try to convert the old TLG system to the new one.
        tlg_config_path = os.path.join(util.get_game_folder(), "config.json")
        tlg_dll = check_tlg(tlg_config_path)
        if tlg_dll:
            print("TLG detected. Attempting to convert to new system.")
            tlg_path = os.path.join(util.get_game_folder(), tlg_dll)
            new_tlg_path = os.path.join(util.get_game_folder(), "tlg.dll")
            if os.path.exists(tlg_path):
                print(f"Renaming {tlg_dll} to tlg.dll")
                shutil.move(tlg_path, new_tlg_path)
                settings.tlg_orig_name = tlg_dll
            
            print("Removing carotene from TLG config.")
            fix_tlg_config(tlg_config_path)
        
        if os.path.exists(os.path.join(util.get_game_folder(), "carotene.dll")):
            print("Deleting carotene.dll")
            os.remove(os.path.join(util.get_game_folder(), "carotene.dll"))
            settings.dll_name = None

        print("Upgrade complete.")


def main(dl_latest=False, dll_name='version.dll', ignore_filesize=False):
    print("=== Patching ===")

    if not os.path.exists(util.MDB_PATH):
        raise SqliteError(f"MDB not found: {util.MDB_PATH}")
    
    upgrade()

    ver = None
    if dl_latest:
        ver = util.download_latest(ignore_filesize, settings.prerelease)

    settings.client_version = version.VERSION
    settings.install_started = True
    settings.customization_changed = False

    mark_mdb_translated(ver)

    import_mdb()

    if pc("assembly"):
        import_assembly()
    
    download_dll(dl_latest, dll_name)

    import_assets()

    if dl_latest:
        util.clean_download()
    
    settings.install_started = False
    settings.installed = True

    print("=== Patching complete! ===\n")


if __name__ == "__main__":
    main(dl_latest=False)
