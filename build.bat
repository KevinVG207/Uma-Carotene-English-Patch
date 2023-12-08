venv\Scripts\activate
cd ./src
python create_version.py
pyinstaller _gui.spec
cd ..