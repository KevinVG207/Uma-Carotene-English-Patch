import pyinstaller_versionfile
import version

def generate():
    pyinstaller_versionfile.create_versionfile(
        output_file="version.rc",
        version=version.VERSION,
        file_description="Carotene English Patcher for Uma Musume",
        internal_name="Carotene Patcher",
        original_filename="Carotene-Patcher.exe",
        product_name="Carotene Patcher"
    )

if __name__ == "__main__":
    generate()
