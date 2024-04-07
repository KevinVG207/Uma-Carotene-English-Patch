from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
import requests
import util
import version

class UmaErrorPopup(qtw.QMessageBox):
    def __init__(self, title: str, message: str, traceback_str: str, msg_icon: qtw.QMessageBox.Icon = qtw.QMessageBox.Icon.Critical):
        super().__init__()
        self.setWindowTitle(title)
        self.setText(f"<b>{message}<br>You may send this error report to the developer to help fix this issue.<br>If an error appears multiple times, please join the <a href=\"https://discord.gg/wvGHW65C6A\">Discord server</a>, because the developer might need your help to fix the issue.</b><br>{traceback_str}")
        upload_button = qtw.QPushButton("Send error report")
        upload_button.clicked.connect(lambda: self.upload_error_report(traceback_str))
        self.addButton(upload_button, qtw.QMessageBox.ButtonRole.ActionRole)
        self.addButton(qtw.QPushButton("Close"), qtw.QMessageBox.ButtonRole.RejectRole)

        msgbox_label = self.findChild(qtw.QLabel, "qt_msgbox_label")
        msgbox_label.setSizePolicy(qtw.QSizePolicy.Expanding, qtw.QSizePolicy.Expanding)
        msgbox_label.setTextFormat(qtc.Qt.TextFormat.RichText)
        msgbox_label.setTextInteractionFlags(qtc.Qt.TextInteractionFlag.TextBrowserInteraction)
        msgbox_label.setOpenExternalLinks(True)

        self.setWindowFlag(qtc.Qt.WindowType.WindowStaysOnTopHint, True)
        self.setIcon(msg_icon)
        self.show()
        self.raise_()

    def upload_error_report(self, traceback_str):
        version_str = version.version_to_string(version.VERSION)
        if util.is_script:
            version_str += ".script"
        resp = requests.post("https://umapyoi.net/api/v1/carotene-patcher/error", json={"traceback": traceback_str, "version": version_str})
        resp.raise_for_status()