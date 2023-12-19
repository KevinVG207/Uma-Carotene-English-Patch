import util
import os
import glob
import shutil
from multiprocessing.pool import Pool
from itertools import repeat
import io
import version
import unity
from PIL import Image, ImageFile
from settings import settings

ImageFile.LOAD_TRUNCATED_IMAGES = True

# def backup_mdb():
#     print("Backing up MDB...")
#     shutil.copy(util.MDB_PATH, util.MDB_PATH + f".{round(time.time())}")


def mark_mdb_translated(ver=None):
    mark_mdb_untranslated()

    if not ver:
        ver = version.version_to_string(version.VERSION)

    settings['installed_version'] = ver

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
    settings['installed_version'] = None

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

def get_current_patch_ver():
    cur_ver = _get_version_from_table()

    if cur_ver:
        return cur_ver
    
    # Check for settings file.
    cur_ver = settings['installed_version']
    if cur_ver:
        return 'partial'

    # Check for any remaining backup files.
    asset_backups = glob.glob(util.DATA_PATH + "\\**\\*.bak", recursive=True)
    if asset_backups:
        cur_ver = 'partial'

    return cur_ver


def import_mdb():
    mdb_jsons = glob.glob(util.MDB_FOLDER + "\\**\\*.json")

    with util.MDBConnection() as (conn, cursor):
        for mdb_json in util.tqdm(mdb_jsons, desc="Importing MDB"):
            path_segments = os.path.normpath(mdb_json).rsplit(".", 1)[0].split(os.sep)
            category = path_segments[-1]
            table = path_segments[-2]

            # Backup the table
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {util.TABLE_BACKUP_PREFIX}{table} AS SELECT * FROM {table};")

            # print(f"Importing {table} {category}")
            data = util.load_json(mdb_json)

            for index, entry in data.items():
                if table != "text_data":
                    # TODO: Implement other tables
                    continue

                # Fix for newlines of slogans.
                if (table, category) == ("text_data", "144"):
                    entry["text"] = "<slogan>" + entry["text"] 

                cursor.execute(
                    f"""UPDATE {table} SET text = ? WHERE category = ? and `index` = ?;""",
                    (entry['text'], category, index)
                )

        conn.commit()
        cursor.execute("VACUUM;")
        conn.commit()

    print("Import complete.")


def clean_asset_backups():
    asset_backups = glob.glob(util.DATA_PATH + "\\**\\*.bak", recursive=True)
    print(f"Amount of backups to revert: {len(asset_backups)}")
    for asset_backup in asset_backups:
        asset_path = asset_backup.rsplit(".", 1)[0]
        if not os.path.exists(asset_path):
            print(f"Deleting {asset_backup}")
            os.remove(asset_backup)
    print("Done")

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
    max_len = max(len(diff_bytes), len(source_bytes))

    diff_bytes = diff_bytes.ljust(max_len, b'\x00')
    source_bytes = source_bytes.ljust(max_len, b'\x00')

    new_bytes = util.xor_bytes(diff_bytes, source_bytes)

    return new_bytes, texture_read

def handle_backup(asset_hash):
    asset_path = util.get_asset_path(asset_hash)
    asset_path_bak = asset_path + ".bak"

    if not os.path.exists(asset_path):
        print(f"Asset not found: {asset_path}")
        return None

    if not os.path.exists(asset_path_bak):
        shutil.copy(asset_path, asset_path_bak)
    else:
        shutil.copy(asset_path_bak, asset_path)
    
    return asset_path

def _import_texture(asset_metadata):
    hash = asset_metadata['hash']
    asset_path = handle_backup(hash)

    if not asset_path:
        return
    
    # print(f"Replacing {os.path.basename(asset_path)}")
    asset_bundle = unity.load_asset(asset_path)
    
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
        texture_read.image = new_image
        texture_read.save()

        new_image_buffer.close()
    
    with open(asset_path, "wb") as f:
        f.write(asset_bundle.file.save(packer="original"))

def import_textures(texture_asset_metadatas):
    print(f"Replacing {len(texture_asset_metadatas)} textures.")

    with Pool() as pool:
        _ = list(util.tqdm(pool.imap_unordered(_import_texture, texture_asset_metadatas, chunksize=16), total=len(texture_asset_metadatas), desc="Importing textures"))


def _import_story(story_data):
    bundle_path = handle_backup(story_data['hash'])

    # print(f"Importing {os.path.basename(bundle_path)}")

    asset_bundle = unity.load_asset(bundle_path)

    root = list(asset_bundle.container.values())[0].get_obj()
    tree = root.read_typetree()

    file_name = story_data['file_name']

    if file_name.startswith("race/"):
        raise NotImplementedError("Race stories(?) not implemented yet.")
    
    tree['Title'] = story_data['title']

    for new_block in story_data['data']:
        block_object = root.assets_file.files[new_block['path_id']]
        block_data = block_object.read_typetree()

        block_data['Text'] = '<story>' + new_block['text']
        block_data['Name'] = new_block['name']

        if new_block.get('clip_length'):
            block_data['ClipLength'] = new_block['clip_length']
        
        if new_block.get('choices'):
            for i, choice in enumerate(block_data['ChoiceDataList']):
                choice['Text'] = new_block['choices'][i]['text']
        
        org_clip_length = block_data['ClipLength']
        new_clip_length = new_block['clip_length']
        
        if new_clip_length > org_clip_length:
            block_data['ClipLength'] = new_clip_length
            new_block_length = new_clip_length + block_data['StartFrame'] + 1
            tree['BlockList'][new_block['block_id']]['BlockLength'] = new_block_length
        
            if new_block.get('anim_data'):
                for anim in new_block['anim_data']:
                    new_anim_length = anim['orig_length'] + new_clip_length - org_clip_length
                    if new_anim_length > anim['orig_length']:
                        anim_asset = root.assets_file.files[anim['path_id']]
                        anim_tree = anim_asset.read_typetree()
                        anim_tree['ClipLength'] = new_anim_length
                        anim_asset.save_typetree(anim_tree)

        block_object.save_typetree(block_data)

    root.save_typetree(tree)

    with open(bundle_path, "wb") as f:
        f.write(asset_bundle.file.save(packer="original"))

def import_stories(story_datas):
    #TODO: Increase chunk size (maybe 16?) when more stories are added.
    with Pool() as pool:
        _ = list(util.tqdm(pool.imap_unordered(_import_story, story_datas, chunksize=2), total=len(story_datas), desc="Importing stories"))

    # print(f"Replacing {len(story_datas)} stories.")
    # for story_data in story_datas:
    #     _import_story(story_data)

def import_assets():
    clean_asset_backups()

    jsons = glob.glob(util.ASSETS_FOLDER + "\\**\\*.json", recursive=True)

    with Pool() as pool:
        results = list(util.tqdm(pool.imap_unordered(util.get_asset_and_type, jsons, chunksize=128), total=len(jsons), desc="Looking for textures"))

    # asset_dict = {result[0]: result[1] for result in results if result[0]}
    asset_dict = {}

    for result in results:
        asset_type, asset_data = result
        if not asset_type:
            continue

        if asset_type not in asset_dict:
            asset_dict[asset_type] = []

        asset_dict[asset_type].append(asset_data)

    import_textures(asset_dict['texture'])
    import_stories(asset_dict['story'])


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


def import_assembly(dl_latest=False, dll_name='version.dll'):
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

    if dl_latest:
        print("Looking for latest mod version")
        latest_data = util.fetch_latest_github_release("KevinVG207", "Uma-Carotenify")
        print("Downloading patcher mod.")

        dll_url = None
        for asset in latest_data['assets']:
            if asset['name'] == 'version.dll':
                dll_url = asset['browser_download_url']
                break
        
        if not dll_url:
            raise Exception("version.dll not found in release assets.")
        
        prev_name = settings['dll_name']
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
        

        dll_path = os.path.join(game_folder, dll_name)
        bak_path = dll_path + util.DLL_BACKUP_SUFFIX

        if os.path.exists(dll_path) and not os.path.exists(bak_path):
            print(f"Backing up existing {dll_name}")
            shutil.move(dll_path, bak_path)
        
        settings['dll_name'] = dll_name
        util.download_file(dll_url, dll_path)
    else:
        print("Not downloading latest dll.")

    print("Done.")


def main(dl_latest=False, dll_name='version.dll'):
    print("=== Patching ===")

    if not os.path.exists(util.MDB_PATH):
        raise FileNotFoundError(f"MDB not found: {util.MDB_PATH}")

    ver = None
    if dl_latest:
        ver = util.download_latest()

    mark_mdb_translated(ver)

    import_mdb()

    import_assembly(dl_latest, dll_name)

    import_assets()

    if dl_latest:
        util.clean_download()
    
    print("=== Patching complete! ===\n")

def test():
    # import_assembly()
    import_assets()

if __name__ == "__main__":
    main(dl_latest=False)
