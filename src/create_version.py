import pyinstaller_versionfile
import version

def generate():
    pyinstaller_versionfile.create_versionfile(
        output_file="version.rc",
        version=version.version_to_string(version.VERSION)[1:],
        file_description="Carotene English Patcher for Uma Musume",
        internal_name="CarotenePatcher",
        original_filename="CarotenePatcher.exe",
        product_name="CarotenePatcher"
    )

if __name__ == "__main__":
    generate()
