from PyQt5.QtCore import *
from PyQt5.QtCore import QObject
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QWidget, QMessageBox
import _patch
import _unpatch
import util
import version
from settings import settings
import enum
import sys
import traceback
import ui.customize_widget as customize_widget
from sqlite3 import Error as SqliteError
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QSize
from ui.error_report import UmaErrorPopup

class PatchStatus(enum.Enum):
    Unpatched = ['Unpatched', 'red']
    Patched = ['Patched TL{} DLL{}', '#00ff00']
    Outdated = ['Outdated TL{} DLL{}', 'orange']
    DllOutdated = ['DLL outdated TL{} DLL{}', 'orange']
    Partial = ['Remnants found, please reapply', 'yellow']
    Unfinished = ['Installation was interrupted', 'yellow']
    DllNotFound = ['DLL not found', 'yellow']
    DllDeprecated = ['DLL deprecated', 'yellow']
    SettingsChanged = ['Customization changed', 'yellow']

class Stream(QObject):
    newText = pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))

class Worker(QObject):
    finished = pyqtSignal()

    def __init__(self, func, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.func = func
        self._parent = parent

    def run(self):
        try:
            self.func()
        except Exception as e:
            self._parent.error = e
            self._parent.traceback = traceback.format_exc()
        self.finished.emit()

class patcher_widget(QWidget):
    def __init__(self, *args, base_widget=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.base_widget = base_widget
        self.background_thread = False
        self.error_handler = None
        self.error = None
        self.traceback = None
        self.ignore_filesize = False
        self.patch_status = PatchStatus.Unpatched

        self.setupUi()
        self.setFixedSize(self.size())

        self.pipe_output()

        # check if dlls exist in current directory
        if util.running_from_game_folder():
            util.display_critical_message("Cannot execute in current directory", "Please make sure to not launch the patcher inside the umamusume install directory!\n\nYou can execute it from anywhere but the umamusume directory.")
            sys.exit()

        try:
            self.update_patch_status()
        except util.GameDatabaseNotFoundException:
            sys.exit()
        
        if settings.args.patch:
            dll_name = settings.args.patch
            if self.patch_status != PatchStatus.Patched or dll_name != settings.dll_name:
                self._patch()
            util.send_finish_signal()
            sys.exit()
        if settings.args.force:
            self._patch()
            util.send_finish_signal()
            sys.exit()
        if settings.args.unpatch:
            self._unpatch()
            util.send_finish_signal()
            sys.exit()
        
        self.show_deprecation_warning()

        self.raise_()
    
    def update_patch_status(self):
        cur_patch_ver, cur_dll_ver = _patch.get_current_patch_ver()
        latest_version_data = util.get_latest_json(settings.prerelease)
        latest_dll_version_data = util.get_latest_dll_json(settings.prerelease)

        if not cur_patch_ver:
            patch_status = PatchStatus.Unpatched
        elif cur_patch_ver == 'partial':
            patch_status = PatchStatus.Partial
        elif cur_patch_ver == 'unfinished':
            patch_status = PatchStatus.Unfinished
        elif cur_patch_ver == 'dllnotfound':
            patch_status = PatchStatus.DllNotFound
        elif not cur_dll_ver:
            patch_status = PatchStatus.Unpatched
        elif settings.dll_name == 'uxtheme.dll':
            patch_status = PatchStatus.DllDeprecated
        else:
            cur_patch_ver = version.string_to_version(cur_patch_ver)
            cur_dll_ver = version.string_to_version(cur_dll_ver)
            latest_ver = version.string_to_version(latest_version_data['tag_name'])

            latest_dll_ver = version.string_to_version(latest_dll_version_data['tag_name'])

            if latest_ver > cur_patch_ver:
                patch_status = PatchStatus.Outdated
            elif latest_dll_ver > cur_dll_ver:
                patch_status = PatchStatus.DllOutdated
            else:
                patch_status = PatchStatus.Patched
        
        if patch_status != PatchStatus.Unpatched and settings.customization_changed:
            patch_status = PatchStatus.SettingsChanged
            
        
        patch_text, patch_color = patch_status.value
        if '{}' in patch_text:
            patch_text = patch_text.format(version.version_to_string(cur_patch_ver), version.version_to_string(cur_dll_ver))

        self.lbl_patch_status_indicator.setStyleSheet(f"background-color: {patch_color};")

        self.lbl_patch_status_2.setText(patch_text)


        if patch_status == PatchStatus.Unpatched:
            self.btn_patch.setText(u"Patch")
        
        elif patch_status == PatchStatus.Outdated or patch_status == PatchStatus.DllOutdated:
            self.btn_patch.setText(u"Update")
        
        else:
            self.btn_patch.setText(u"Reapply")
    
        if patch_status == PatchStatus.Unpatched:
            self.lbl_patch_status_3.setText(f"Install the latest patch version.")
        elif patch_status == PatchStatus.Patched:
            self.lbl_patch_status_3.setText(f"Latest version is installed!")
        elif patch_status == PatchStatus.Outdated:
            self.lbl_patch_status_3.setText(f"<b>Update to TL {latest_version_data['tag_name']} now!</b>")
        elif patch_status == PatchStatus.DllOutdated:
            self.lbl_patch_status_3.setText(f"<b>Update to DLL {latest_dll_version_data['tag_name']} now!</b>")
        elif patch_status == PatchStatus.Partial:
            self.lbl_patch_status_3.setText(f"Your patch is incomplete, possibly due to a game update.")
        elif patch_status == PatchStatus.Unfinished:
            self.lbl_patch_status_3.setText(f"Your patch was interrupted. Please reapply.")
        elif patch_status == PatchStatus.DllNotFound:
            self.lbl_patch_status_3.setText(f"Your DLL is missing. Please reapply.")
        elif patch_status == PatchStatus.DllDeprecated:
            self.lbl_patch_status_3.setText(f"Your DLL no longer works. Please reapply.")
        elif patch_status == PatchStatus.SettingsChanged:
            self.lbl_patch_status_3.setText(f"You changed the customization. Please reapply.")
        
        self.patch_status = patch_status


    def pipe_output(self):
        if not util.is_script:
            sys.stdout = Stream(newText=self.onUpdateText)
            sys.stderr = Stream(newText=self.onUpdateText)
    
    def onUpdateText(self, text):
        self.plainTextEdit.moveCursor(QTextCursor.End)
        self.plainTextEdit.insertPlainText(text)
        self.plainTextEdit.moveCursor(QTextCursor.End)
    
    def clean_thread(self):
        self.background_thread = False

        if self.error:
            print(self.traceback)
            if self.error_handler:
                self.error_handler(self.error)

        self.error_handler = None
        self.error = None
        self.traceback = None
        self.btn_patch.setEnabled(True)
        self.btn_revert.setEnabled(True)
        self.btn_settings.setEnabled(True)

    def try_start_thread(self, func, error_handler=None):
        if self.background_thread:
            return
        
        if not util.close_umamusume():
            print("Error: The game is still running.")
            return
        
        self.btn_patch.setEnabled(False)
        self.btn_revert.setEnabled(False)
        self.btn_settings.setEnabled(False)
        
        self.background_thread = True
        self.error_handler = error_handler
        self.thread_ = QThread()
        self.worker = Worker(func, self)
        
        self.worker.moveToThread(self.thread_)
        self.thread_.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread_.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread_.finished.connect(self.thread_.deleteLater)
        self.thread_.finished.connect(self.clean_thread)
        self.thread_.finished.connect(self.update_patch_status)
        self.thread_.start()

    def _patch(self):
        if settings.customization_changed:
            _unpatch.main(dl_latest=True)
            settings.customization_changed = False
        _patch.main(dl_latest=True, ignore_filesize=self.ignore_filesize)

    def patch(self):
        if settings.first_run:
            # Show a disclaimer
            msgbox = QMessageBox(self)
            msgbox.setIcon(QMessageBox.Information)
            msgbox.setWindowTitle("Disclaimer")
            msgbox.setText("""
<b>Please read and accept the following:</b><br>
<br>
By using Carotene Patcher, you agree to also install <a href="https://github.com/Hachimi-Hachimi/Cellar">Cellar modloader</a> (if not already installed).<br>
Cellar is not affiliated with Carotene Patcher and is a separate project by a different developer.<br>
<br>
Furthermore, know that any modifications to the game are against its Terms of Service.<br>
The developers/contributors of Carotene English Patch are not responsible for any consequences that may arise from using this patcher.<br>
Use at your own risk.""")

            msgbox.addButton("Agree && don't show again", QMessageBox.YesRole)
            no_btn = msgbox.addButton("Cancel", QMessageBox.NoRole)
            msgbox.setDefaultButton(no_btn)

            msgbox.exec()

            if msgbox.clickedButton() == no_btn:
                return
            settings.first_run = False

        self.try_start_thread(lambda: self._patch(), error_handler=self.patch_error)
    
    def _unpatch(self):
        _unpatch.main(dl_latest=True)

    def unpatch(self):
        self.try_start_thread(self._unpatch)

    def closeEvent(self, event):
        if self.background_thread:
            QMessageBox.critical(self, "Cannot Close", "Please wait for the patcher to finish.", QMessageBox.Ok)
            event.ignore()
            return
    
    def patch_error(self, e):
        if isinstance(e, SqliteError):
            res = QMessageBox.warning(self, "Database Error", "An error occurred while patching the game's database.<br>It may be invalid. Do you want to redownload the database?", QMessageBox.Yes | QMessageBox.No)
            if res == QMessageBox.Yes:
                self.try_start_thread(lambda: util.redownload_mdb())
                return
        
        util.send_error_signal(str(e))
        
        if isinstance(e, util.NotEnoughSpaceException):
            # Get error message
            error_message = str(e)

            res = QMessageBox.warning(self, "Not Enough Space", error_message, QMessageBox.Ok)
            self.ignore_filesize = True
        
        else:
            if not settings.has_args():
                util.run_widget(UmaErrorPopup(title="Error", message="An error occurred while running the patcher.", traceback_str=self.traceback.replace("\n", "<br>")))

    def show_settings(self):
        self.settings_widget = customize_widget.customize_widget(self)
        self.settings_widget.setModal(True)  # Set the widget to be modal
        self.settings_widget.show()

    def setupUi(self):
        if not self.objectName():
            self.setObjectName(u"widget_main")
        self.resize(461, 231)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QSize(221, 131))
        self.setWindowTitle(f"Carotene English Patcher for Uma Musume {version.version_to_string(version.VERSION)}")
        self.setLayoutDirection(Qt.LeftToRight)
        self.lbl_patch_status_indicator = QLabel(self)
        self.lbl_patch_status_indicator.setObjectName(u"lbl_patch_status_indicator")
        self.lbl_patch_status_indicator.setGeometry(QRect(140, 10, 21, 20))
        sizePolicy.setHeightForWidth(self.lbl_patch_status_indicator.sizePolicy().hasHeightForWidth())
        self.lbl_patch_status_indicator.setSizePolicy(sizePolicy)
        self.lbl_patch_status_indicator.setMinimumSize(QSize(20, 20))
        self.lbl_patch_status_indicator.setStyleSheet(f"background-color: red;")
        self.lbl_patch_status_indicator.setText(u"")
        self.lbl_patch_status_2 = QLabel(self)
        self.lbl_patch_status_2.setObjectName(u"lbl_patch_status_2")
        self.lbl_patch_status_2.setGeometry(QRect(170, 10, 281, 21))
        self.lbl_patch_status_2.setText("")

        self.btn_revert = QPushButton(self)
        self.btn_revert.setObjectName(u"btn_revert")
        self.btn_revert.setGeometry(QRect(240, 70, 83, 31))
        self.btn_revert.setText(u"Unpatch")
        self.btn_revert.clicked.connect(self.unpatch)

        self.btn_patch = QPushButton(self)
        self.btn_patch.setObjectName(u"btn_patch")
        self.btn_patch.setGeometry(QRect(140, 70, 83, 31))
        
        self.btn_patch.clicked.connect(self.patch)

        self.lbl_patch_status_3 = QLabel(self)
        self.lbl_patch_status_3.setObjectName(u"lbl_patch_status_3")
        self.lbl_patch_status_3.setGeometry(QRect(140, 40, 311, 21))

        self.plainTextEdit = QPlainTextEdit(self)
        self.plainTextEdit.setObjectName(u"plainTextEdit")
        self.plainTextEdit.setGeometry(QRect(10, 110, 441, 111))
        self.plainTextEdit.setReadOnly(True)
        self.plainTextEdit.setPlaceholderText(u"Log will go here.")
        # Set font to Consolas with a size of 10
        font = QFont()
        font.setFamily(u"Consolas")
        font.setPointSize(8)
        self.plainTextEdit.setFont(font)


        self.btn_settings = QPushButton(self)
        self.btn_settings.setObjectName(u"btn_settings")
        self.btn_settings.setGeometry(QRect(370, 10, 83, 31))
        self.btn_settings.setText(u"Customization")
        self.btn_settings.clicked.connect(self.show_settings)

    def show_deprecation_warning(self):
        # Warning box
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Warning)
        msgbox.findChild(QLabel).setOpenExternalLinks(True)
        msgbox.setWindowTitle("Carotene end of life")
        msgbox.setText("""
<h2>Support for Carotene English Patch has ended</h2>
<p>Carotene English Patch will no longer receive updates. Thank you for using my mod!</p>
<p>Carotene has merged with <b><a href="https://hachimi.leadrdrk.com/">Hachimi</a></b> and translation updates will continue there.</p>
<p>A bit more info on the merge and the end of Carotene can be found on <a href="https://umapyoi.net/carotene-english-patch">Carotene's webpage.</a></p>
<p><b>Please unpatch Carotene before installing Hachimi!</b></p>""")
        msgbox.addButton("OK", QMessageBox.AcceptRole)
        msgbox.exec()
