from PySide6 import QtWidgets, QtCore, QtGui
import sys
import os
from spritesheet_builder.builder_app import BuilderApp


def main():
    QtCore.QCoreApplication.setOrganizationName("AISpritesheet")
    QtCore.QCoreApplication.setApplicationName("Sprite Sheet Builder")
    app = QtWidgets.QApplication(sys.argv)

    window = BuilderApp()
    window.resize(1200, 800)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
