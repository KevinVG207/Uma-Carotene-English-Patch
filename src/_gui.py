# Hack for fixing multiprocessing with PyInstaller
import multiprocessing
multiprocessing.freeze_support()

from ui.widget_main import patcher_widget
import util
import version

def main():
    version.check_update()
    util.run_widget(patcher_widget)

if __name__ == "__main__":
    main()
