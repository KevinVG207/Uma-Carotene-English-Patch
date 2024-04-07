# Hack for fixing multiprocessing with PyInstaller
import multiprocessing
multiprocessing.freeze_support()
import traceback

from ui.widget_main import patcher_widget
from ui.customize_widget import customize_widget
from ui.error_report import UmaErrorPopup
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
        traceback_str = traceback.format_exc().replace("\n", "<br>")
        util.send_error_signal(traceback_str)
        if not settings.has_args():
            util.run_widget(UmaErrorPopup(title="Error", message="An error occurred while running the patcher.", traceback_str=traceback_str))

if __name__ == "__main__":
    main()
