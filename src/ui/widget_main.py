import typing
from PyQt5.QtCore import *
from PyQt5.QtCore import QObject
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QWidget
import _patch
import _unpatch
import util
import version
import enum
import sys
import traceback

class PatchStatus(enum.Enum):
    Unpatched = ['Unpatched', 'red']
    Patched = ['Patched {}', '#00ff00']
    Outdated = ['Outdated {}', 'orange']
    Partial = ['Remnants found, please reapply', 'yellow']

class Stream(QObject):
    newText = pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))

class Worker(QObject):
    finished = pyqtSignal()

    def __init__(self, func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.func = func

    def run(self):
        try:
            self.func()
        except Exception:
            traceback.print_exc()
        self.finished.emit()

class patcher_widget(QWidget):
    def __init__(self, *args, base_widget=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.base_widget = base_widget
        self.background_thread = False

        self.setupUi()
        self.setFixedSize(self.size())

        self.pipe_output()
        self.update_patch_status()
    
    def update_patch_status(self):
        current_version = _patch.get_current_patch_ver()
        latest_version_data = util.get_latest_json()

        if not current_version:
            patch_status = PatchStatus.Unpatched
        elif current_version == 'partial':
            patch_status = PatchStatus.Partial
        else:
            cur_ver = version.string_to_version(current_version)
            latest_ver = version.string_to_version(latest_version_data['tag_name'])

            if latest_ver > cur_ver:
                patch_status = PatchStatus.Outdated
            else:
                patch_status = PatchStatus.Patched
        
        patch_text, patch_color = patch_status.value
        if '{}' in patch_text:
            patch_text = patch_text.format(current_version)

        self.lbl_patch_status_indicator.setStyleSheet(f"background-color: {patch_color};")

        self.lbl_patch_status_2.setText(patch_text)


        if patch_status == PatchStatus.Unpatched:
            self.btn_patch.setText(u"Patch")
        
        elif patch_status in (PatchStatus.Patched, PatchStatus.Partial):
            self.btn_patch.setText(u"Reapply")
        
        elif patch_status == PatchStatus.Outdated:
            self.btn_patch.setText(u"Update")
    
        if patch_status == PatchStatus.Unpatched:
            self.lbl_patch_status_3.setText(f"Install {latest_version_data['tag_name']} now!")
        elif patch_status == PatchStatus.Patched:
            self.lbl_patch_status_3.setText(f"Latest version is installed!")
        elif patch_status == PatchStatus.Outdated:
            self.lbl_patch_status_3.setText(f"<b>Update to {latest_version_data['tag_name']} now!</b>")
        elif patch_status == PatchStatus.Partial:
            self.lbl_patch_status_3.setText(f"Your patch is incomplete, possibly due to a game update.")


    def pipe_output(self):
        sys.stdout = Stream(newText=self.onUpdateText)
        sys.stderr = Stream(newText=self.onUpdateText)
    
    def onUpdateText(self, text):
        self.plainTextEdit.moveCursor(QTextCursor.End)
        self.plainTextEdit.insertPlainText(text)
        self.plainTextEdit.moveCursor(QTextCursor.End)
    
    def clean_thread(self):
        self.background_thread = False
        self.btn_patch.setEnabled(True)
        self.btn_revert.setEnabled(True)

    def try_start_thread(self, func):
        if self.background_thread:
            return
        
        if not util.close_umamusume():
            print("Error: The game is still running.")
            return
        
        self.btn_patch.setEnabled(False)
        self.btn_revert.setEnabled(False)
        
        self.background_thread = True
        self.thread_ = QThread()
        self.worker = Worker(func)
        
        self.worker.moveToThread(self.thread_)
        self.thread_.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread_.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread_.finished.connect(self.thread_.deleteLater)
        self.thread_.finished.connect(self.clean_thread)
        self.thread_.finished.connect(self.update_patch_status)
        self.thread_.start()

    def patch(self):
        self.try_start_thread(lambda: _patch.main(dl_latest=True))
    
    def unpatch(self):
        self.try_start_thread(lambda: _unpatch.main())

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
