from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QApplication, QStyleFactory, QWidget, QVBoxLayout, QLabel
import sys

class TransparentWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Window Dimensions and Flags
        self.resize(500, 200)  # Sets the boundary box for your text
        QApplication.setStyle(QStyleFactory.create('Fusion'))
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 2. Force completely transparent backgrounds on everything
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: transparent;
                border: none;
            }
            QLabel {
                color: #00FF00; /* Neon green text */
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 32px;
                font-weight: bold;
                background: transparent;
                border: none;
            }
        """)

        # 3. Create the Layout and Solid Text
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        layout = QVBoxLayout(self.central_widget)
        self.label = QLabel("Floating Transparent Text", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TransparentWindow()
    window.show()
    sys.exit(app.exec())