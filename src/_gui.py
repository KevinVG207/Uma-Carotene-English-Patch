# Hack for fixing multiprocessing with PyInstaller
import multiprocessing
multiprocessing.freeze_support()

from ui.widget_main import patcher_widget
from ui.customize_widget import customize_widget
import util
import version
from settings import settings

def main():
    util.send_start_signal()
    try:
        if settings.args.customization:
            util.run_widget(customize_widget, main=True)
            util.send_finish_signal()
            return
        
        version.check_update()
        util.run_widget(patcher_widget)
    except Exception as e:
        util.send_error_signal(str(e))
        raise e

if __name__ == "__main__":
    main()
