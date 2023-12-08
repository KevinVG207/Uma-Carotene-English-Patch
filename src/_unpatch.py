import util
import glob
import shutil
import os
import _patch

def revert_mdb():
    print("Reverting MDB")
    with util.MDBConnection() as (conn, cursor):
        # Restore tables starting with "patch_backup_"
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '{util.TABLE_BACKUP_PREFIX}%';")
        tables = cursor.fetchall()
        if not tables:
            return

        for table in tables:
            table = table[0]
            print(f"Restoring {table}")
            # Copy the backup table to the original table
            cursor.execute(f"SELECT * FROM {table};")
            rows = cursor.fetchall()
            
            normal_table = table[len(util.TABLE_BACKUP_PREFIX):]
            # Chunk the rows
            for i in range(0, len(rows), 1000):
                chunk = rows[i:i+1000]
                cursor.executemany(f"INSERT OR REPLACE INTO {normal_table} VALUES ({','.join(['?']*len(chunk[0]))});", chunk)

            # Delete the backup table
            cursor.execute(f"DROP TABLE {table};")

        conn.commit()
        cursor.execute("VACUUM;")
        conn.commit()

def revert_assets():
    asset_backups = glob.glob(util.DATA_PATH + "\\**\\*.bak", recursive=True)
    print(f"Reverting {len(asset_backups)} assets")
    for asset_backup in asset_backups:
        asset_path = asset_backup.rsplit(".", 1)[0]
        if not os.path.exists(asset_path):
            # print(f"Deleting {asset_backup}")
            os.remove(asset_backup)
        else:
            # print(f"Reverting {asset_path}")
            shutil.copy(asset_backup, asset_path)
            os.remove(asset_backup)


def revert_assembly():
    print("Reverting translations.txt")
    game_folder = util.get_game_folder()

    if not game_folder:
        print("Game folder could not be determined. Skipping.")
        return

    if not os.path.exists(game_folder):
        print(f"Game folder {game_folder} does not exist. Skipping.")
        return

    translations_path = os.path.join(game_folder, "translations.txt")
    dll_path = os.path.join(game_folder, "version.dll")

    if not os.path.exists(translations_path):
        print("translations.txt does not exist. Skipping.")
    else:
        os.remove(translations_path)

    print("Deleting version.dll")
    if not os.path.exists(dll_path):
        print("version.dll does not exist. Skipping.")
    else:
        os.remove(dll_path)


def main():
    print("=== Unpatching ===")
    revert_mdb()
    revert_assets()
    revert_assembly()
    _patch.mark_mdb_untranslated()
    print("=== Unpatch complete! ===\n")

if __name__ == "__main__":
    main()
