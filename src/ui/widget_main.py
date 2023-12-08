from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QWidget
import _import
import _revert
import _update_local
import _prepare_release
import version

class Ui_widget_main(QWidget):
    def __init__(self, *args, base_widget=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.base_widget = base_widget

        self.setupUi(self)
        self.setFixedSize(self.size())

    def check_patched(self):
        cur_ver = _import.is_mdb_translated()
        if cur_ver:
            self.lbl_patch_status_indicator.setStyleSheet(u"background-color: rgb(0, 170, 0);")
            self.lbl_patch_status_2.setText(f"Patched with {version.version_to_string(cur_ver)}")
        else:
            self.lbl_patch_status_indicator.setStyleSheet(u"background-color: rgb(255, 0, 0);")
            self.lbl_patch_status_2.setText(u"Unpatched")
    
    def index_clicked(self):
        self.base_widget.refresh_widgets(_update_local.main)
        self.check_patched()
    
    def commit_clicked(self):
        self.base_widget.refresh_widgets(_prepare_release.main)

    def patch_clicked(self):
        self.setCursor(Qt.WaitCursor)
        _import.main()
        self.check_patched()
        self.unsetCursor()

    def revert_clicked(self):
        self.setCursor(Qt.WaitCursor)
        _revert.main()
        self.check_patched()
        self.unsetCursor()

    def setupUi(self, widget_main):
        if not widget_main.objectName():
            widget_main.setObjectName(u"widget_main")
        widget_main.resize(401, 349)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(widget_main.sizePolicy().hasHeightForWidth())
        widget_main.setSizePolicy(sizePolicy)
        widget_main.setMinimumSize(QSize(401, 349))
        widget_main.setWindowTitle(u"Widget Main")
        widget_main.setLayoutDirection(Qt.LeftToRight)
        self.lbl_patch_status_indicator = QLabel(widget_main)
        self.lbl_patch_status_indicator.setObjectName(u"lbl_patch_status_indicator")
        self.lbl_patch_status_indicator.setGeometry(QRect(110, 120, 21, 20))
        sizePolicy.setHeightForWidth(self.lbl_patch_status_indicator.sizePolicy().hasHeightForWidth())
        self.lbl_patch_status_indicator.setSizePolicy(sizePolicy)
        self.lbl_patch_status_indicator.setMinimumSize(QSize(20, 20))
        self.lbl_patch_status_indicator.setStyleSheet(u"background-color: rgb(255, 106, 0);")
        self.lbl_patch_status_indicator.setText(u"")
        self.lbl_patch_status_2 = QLabel(widget_main)
        self.lbl_patch_status_2.setObjectName(u"lbl_patch_status_2")
        self.lbl_patch_status_2.setGeometry(QRect(140, 120, 151, 21))
        self.lbl_patch_status_2.setText(u"Unpatched")
        self.lbl_contribute = QLabel(widget_main)
        self.lbl_contribute.setObjectName(u"lbl_contribute")
        self.lbl_contribute.setGeometry(QRect(110, 210, 181, 21))
        self.lbl_contribute.setText(u"Contribute")
        self.lbl_contribute.setAlignment(Qt.AlignCenter)
        self.btn_revert = QPushButton(widget_main)
        self.btn_revert.setObjectName(u"btn_revert")
        self.btn_revert.setGeometry(QRect(210, 150, 83, 31))
        self.btn_revert.setText(u"Revert")
        self.btn_revert.clicked.connect(self.revert_clicked)

        self.btn_patch = QPushButton(widget_main)
        self.btn_patch.setObjectName(u"btn_patch")
        self.btn_patch.setGeometry(QRect(110, 150, 83, 31))
        self.btn_patch.setText(u"Patch")
        self.btn_patch.clicked.connect(self.patch_clicked)

        self.lbl_update_indicator = QLabel(widget_main)
        self.lbl_update_indicator.setObjectName(u"lbl_update_indicator")
        self.lbl_update_indicator.setGeometry(QRect(110, 30, 20, 21))
        sizePolicy.setHeightForWidth(self.lbl_update_indicator.sizePolicy().hasHeightForWidth())
        self.lbl_update_indicator.setSizePolicy(sizePolicy)
        self.lbl_update_indicator.setMinimumSize(QSize(20, 20))
        self.lbl_update_indicator.setStyleSheet(u"background-color: rgb(255, 0, 0);")
        self.lbl_update_indicator.setText(u"")
        self.lbl_update_text = QLabel(widget_main)
        self.lbl_update_text.setObjectName(u"lbl_update_text")
        self.lbl_update_text.setGeometry(QRect(140, 30, 142, 20))
        sizePolicy1 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.lbl_update_text.sizePolicy().hasHeightForWidth())
        self.lbl_update_text.setSizePolicy(sizePolicy1)
        self.lbl_update_text.setText(u"No update available")
        self.btn_commit = QPushButton(widget_main)
        self.btn_commit.setObjectName(u"btn_commit")
        self.btn_commit.setGeometry(QRect(220, 240, 81, 31))
        self.btn_commit.setText(u"Commit Edits")
        self.btn_commit.clicked.connect(self.commit_clicked)

        self.btn_update = QPushButton(widget_main)
        self.btn_update.setObjectName(u"btn_update")
        self.btn_update.setGeometry(QRect(110, 60, 81, 31))
        self.btn_update.setText(u"Update")
        self.btn_index = QPushButton(widget_main)
        self.btn_index.setObjectName(u"btn_index")
        self.btn_index.setGeometry(QRect(100, 240, 101, 31))
        self.btn_index.setText(u"Index Game Text")
        self.btn_index.clicked.connect(self.index_clicked)

        self.line = QFrame(widget_main)
        self.line.setObjectName(u"line")
        self.line.setGeometry(QRect(100, 200, 201, 16))
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.retranslateUi(widget_main)

        QMetaObject.connectSlotsByName(widget_main)

        self.check_patched()
    # setupUi

    def retranslateUi(self, widget_main):
        pass
    # retranslateUi

