from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from ui.widget_main import patcher_widget

def main():
    app = QApplication([])
    app.setWindowIcon(QIcon('assets/icon.ico'))
    widget = patcher_widget()
    widget.show()
    app.exec_()

if __name__ == "__main__":
    main()
