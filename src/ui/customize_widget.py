from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from settings import settings


class customize_widget(QDialog):
    def __init__(self, _parent, *args, **kwargs):
        self._parent = _parent
        self.initial_settings = settings.patch_customization
        self.initial_enabled = settings.patch_customization_enabled

        super().__init__(*args, **kwargs)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setupUi(self)
        self.setFixedSize(self.size())

    def save_clicked(self):
        if self.rbtn_all.isChecked():
            settings.patch_customization_enabled = False
        else:
            settings.patch_customization_enabled = True
            tmp_settings = {}
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                tmp_settings[item.data(Qt.UserRole)] = item.checkState() == Qt.Checked
            settings.patch_customization = tmp_settings
        self.close()
    
    def closeEvent(self, event):
        if settings.patch_customization != self.initial_settings or settings.patch_customization_enabled != self.initial_enabled:
            settings.customization_changed = True
        else:
            settings.customization_changed = False
        
        self._parent.update_patch_status()

        event.accept()
    
    def close_clicked(self):
        self.close()

    def select_all_clicked(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Checked)

    def unselect_all_clicked(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Unchecked)
    
    def handle_toggle(self, checked):
        self.list_widget.setEnabled(checked)
        self.btn_select_all.setEnabled(checked)
        self.btn_unselect_all.setEnabled(checked)

    def setupUi(self, customize_dialog):
        customize_dialog.setObjectName(u"customize_dialog")
        customize_dialog.resize(410, 521)
        customize_dialog.setWindowTitle(u"Customize Patch")
        self.verticalLayoutWidget = QWidget(customize_dialog)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(10, 10, 391, 461))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.rbtn_all = QRadioButton(self.verticalLayoutWidget)
        self.rbtn_all.setObjectName(u"rbtn_all")
        self.rbtn_all.setText(u"Patch everything")

        self.verticalLayout.addWidget(self.rbtn_all)

        self.rbtn_customize = QRadioButton(self.verticalLayoutWidget)
        self.rbtn_customize.setObjectName(u"rbtn_customize")
        self.rbtn_customize.setText(u"Patch only the following:")
        self.rbtn_customize.toggled.connect(self.handle_toggle)

        self.verticalLayout.addWidget(self.rbtn_customize)

        self.list_widget = QListWidget(self.verticalLayoutWidget)

        def add_listitem(text, id):
            # Get current state
            checked = settings.patch_customization.get(id, True)

            item = QListWidgetItem(self.list_widget)
            item.setData(Qt.UserRole, id)
            item.setText(text)
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        
        add_listitem("Skill names", "skill_names")
        add_listitem("Skill descriptions", "skill_descs")
        add_listitem("All database (UI) text not in the settings above", "mdb")
        add_listitem("Assembly Strings (UI)", "assembly")
        add_listitem("Flash (UI)", "flash")
        add_listitem("Stories", "story")
        add_listitem("Textures", "textures")

        self.list_widget.setObjectName(u"list_widget")
        self.list_widget.setEnabled(False)

        self.verticalLayout.addWidget(self.list_widget)

        self.btn_save = QPushButton(customize_dialog)
        self.btn_save.setObjectName(u"btn_save")
        self.btn_save.setGeometry(QRect(240, 480, 81, 31))
        self.btn_save.setText(u"Save && Exit")
        self.btn_save.clicked.connect(self.save_clicked)

        self.btn_close = QPushButton(customize_dialog)
        self.btn_close.setObjectName(u"btn_close")
        self.btn_close.setGeometry(QRect(330, 480, 71, 31))
        self.btn_close.setText(u"Cancel")
        self.btn_close.clicked.connect(self.close_clicked)

        self.btn_select_all = QPushButton(customize_dialog)
        self.btn_select_all.setObjectName(u"btn_select_all")
        self.btn_select_all.setEnabled(False)
        self.btn_select_all.setGeometry(QRect(310, 30, 41, 23))
        self.btn_select_all.setText(u"All")
        self.btn_select_all.clicked.connect(self.select_all_clicked)

        self.btn_unselect_all = QPushButton(customize_dialog)
        self.btn_unselect_all.setObjectName(u"btn_unselect_all")
        self.btn_unselect_all.setEnabled(False)
        self.btn_unselect_all.setGeometry(QRect(360, 30, 41, 23))
        self.btn_unselect_all.setText(u"None")
        self.btn_unselect_all.clicked.connect(self.unselect_all_clicked)

        if settings.patch_customization_enabled:
            self.rbtn_customize.setChecked(True)
        else:
            self.rbtn_all.setChecked(True)