from PyQt5.QtCore import *
from PyQt5.QtCore import QObject
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QWidget

class update_widget(QWidget):
    choice = None

    def __init__(self, release_version, choice):
        super().__init__()
        self.choice = choice

        # Init defaults
        self.setWindowTitle("Updating Carotene")

        # Init unique
        self.init_ui(release_version)

        # Generate geometry before showing, otherwise centering doesn't work
        self.adjustSize()

        # Center widget to primary screen
        screen = QDesktopWidget().primaryScreen()
        screen_size = QDesktopWidget().screenGeometry(screen)
        self.move(screen_size.center() - self.rect().center())

        self.raise_()

    def init_ui(self, release_version):
        self.setWindowTitle("Update Available")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        # Set minimum width
        self.setMinimumWidth(300)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel(f"""A new version of Carotene Patcher was found: <a href="https://github.com/KevinVG207/Uma-Carotene-English-Patch/releases/tag/{release_version}">{release_version}</a><br>Update now?""")
        self.label.setWordWrap(True)
        # Center label text
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setOpenExternalLinks(True)
        self.layout.addWidget(self.label)

        self.button_layout = QHBoxLayout()
        self.layout.addLayout(self.button_layout)

        self.update_button = QPushButton("Yes")
        self.update_button.clicked.connect(self._yes)
        self.update_button.setDefault(True)
        self.button_layout.addWidget(self.update_button)

        self.cancel_button = QPushButton("No")
        self.cancel_button.clicked.connect(self._no)
        self.button_layout.addWidget(self.cancel_button)

        # Hide maxminize and minimize buttons
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)


    @pyqtSlot()
    def _yes(self):
        self.choice.append(True)
        self.close()

    @pyqtSlot()
    def _no(self):
        self.choice.append(False)
        self.close()


class update_wait_widget(QWidget):
    update_object = None
    timer = None

    def __init__(self, update_object):
        super().__init__()
        self.update_object = update_object

        # Init defaults
        self.setWindowTitle("Updating Carotene")

        # Init unique
        self.init_ui()

        # Generate geometry before showing, otherwise centering doesn't work
        self.adjustSize()

        # Center widget to primary screen
        screen = QDesktopWidget().primaryScreen()
        screen_size = QDesktopWidget().screenGeometry(screen)
        self.move(screen_size.center() - self.rect().center())

        self.raise_()

    def init_ui(self):
        self.setWindowTitle("Updating")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel("Please wait while Carotene Patcher updates...")
        self.label.setWordWrap(False)

        # Center label text
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setContentsMargins(10, 20, 10, 20)
        self.layout.addWidget(self.label)

        # Hide maxminize and minimize buttons
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)

        # Call function every 250 ms
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self._update)
        self.timer.start()

    @pyqtSlot()
    def _update(self):
        if self.update_object.close_me:
            self.timer.stop()
            self.close()
