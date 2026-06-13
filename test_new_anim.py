import sys
import math
import threading
import numpy as np
import sounddevice as sd

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QFont
from PyQt6.QtWidgets import QApplication, QWidget, QStyleFactory


# ================= AUDIO ENGINE =================
class AudioEngine:
    def __init__(self, callback):
        self.callback = callback
        self.running = True

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self.running = False

    def _run(self):
        def audio_callback(indata, frames, time, status):
            if not self.running:
                return
            volume = np.linalg.norm(indata) * 10
            self.callback(volume)

        with sd.InputStream(channels=1, callback=audio_callback):
            while self.running:
                sd.sleep(50)


# ================= JARVIS WIDGET =================
class JarvisWidget(QWidget):
    def __init__(self):
        super().__init__(None)

        QApplication.setStyle(QStyleFactory.create("Fusion"))

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.BypassWindowManagerHint
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.setFixedSize(420, 420)

        # ===== state =====
        self.t = 0.0
        self.rms = 0.0
        self.rms_smooth = 0.0
        self.state = "idle"

        # ===== audio =====
        self.audio = AudioEngine(self.set_rms)
        self.audio.start()

        # ===== loop =====
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)

        self.move_bottom_right()

    # ================= POSITION =================
    def move_bottom_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.right() - self.width() - 20,
            screen.bottom() - self.height() - 20
        )

    # ================= AUDIO =================
    def set_rms(self, rms):
        self.rms = float(rms)

    # ================= LOOP =================
    def tick(self):
        self.t += 0.02

        target = min(1.0, self.rms / 5000.0)
        self.rms_smooth += (target - self.rms_smooth) * 0.15

        if self.rms_smooth < 0.05:
            self.state = "idle"
        elif self.rms_smooth < 0.25:
            self.state = "listening"
        else:
            self.state = "speaking"

        self.update()

    # ================= WAVEFORM (FIXED) =================
    def waveform_ring(self, p, cx, cy, base_r, points, energy, speed, color):
        energy_amp = 3 + energy * 25  # controlled amplitude (important)

        for i in range(points):
            ang = (i / points) * math.tau

            # center radius stays fixed (THIS is key fix)
            x_base = cx + math.cos(ang) * base_r
            y_base = cy + math.sin(ang) * base_r

            # perpendicular direction (radial outward only)
            nx = math.cos(ang)
            ny = math.sin(ang)

            wave = math.sin(self.t * speed + i * 0.35)

            offset = wave * energy_amp

            x = x_base + nx * offset
            y = y_base + ny * offset

            j = (i + 1) % points
            ang2 = (j / points) * math.tau

            x_base2 = cx + math.cos(ang2) * base_r
            y_base2 = cy + math.sin(ang2) * base_r

            nx2 = math.cos(ang2)
            ny2 = math.sin(ang2)

            wave2 = math.sin(self.t * speed + j * 0.35)
            offset2 = wave2 * energy_amp

            x2 = x_base2 + nx2 * offset2
            y2 = y_base2 + ny2 * offset2

            alpha = int(90 + energy * 180)

            p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), alpha), 2))
            p.drawLine(QPointF(x, y), QPointF(x2, y2))
    # ================= RING DRAW =================
    def ring(self, p, cx, cy, r, w, span, rot, color, glow=0):
        pen = QPen(color, w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2),
                  int(rot * 16), int(span * 16))

        if glow:
            gp = QPen(QColor(color.red(), color.green(), color.blue(), 80),
                      w + 6)
            gp.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(gp)
            p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2),
                      int(rot * 16), int(span * 16))

    # ================= PAINT =================
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.fillRect(self.rect(), Qt.GlobalColor.transparent)

        cx, cy = self.width() / 2, self.height() / 2

        color = QColor(0, 200, 255, 200)

        pulse = 1.0 + self.rms_smooth * 1.5

        # ===== SPEED =====
        speed = 1.0
        if self.state == "listening":
            speed = 2.0
        elif self.state == "speaking":
            speed = 3.5

        # ===== CORE ORB =====
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawEllipse(QPointF(cx, cy), 120, 120)

        # ===== WAVE (FIXED INSIDE INNER RING) =====
        self.waveform_ring(
            p,
            cx,
            cy,
            base_r=110,
            points=120,
            energy=self.rms_smooth,
            speed=3.0 * speed,
            color=color
        )

        # ===== OUTER RINGS =====
        self.ring(p, cx, cy, 175 * pulse, 2, 300, self.t * 40 * speed, color, glow=1)
        self.ring(p, cx, cy, 145 * pulse, 5, 360, self.t * 120 * speed, color, glow=1)
        self.ring(p, cx, cy, 125 * pulse, 3, 220, -self.t * 180 * speed, color, glow=1)

        # ===== TICK RING =====
        for i in range(48):
            ang = math.radians(i * 7.5 + self.t * 30 * speed)

            r1, r2 = 178 * pulse, 186 * pulse

            x1 = cx + math.cos(ang) * r1
            y1 = cy + math.sin(ang) * r1
            x2 = cx + math.cos(ang) * r2
            y2 = cy + math.sin(ang) * r2

            alpha = int(80 + self.rms_smooth * 180)

            p.setPen(QPen(QColor(0, 255, 255, alpha), 2))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ===== TEXT =====
        p.setPen(QColor(220, 255, 255, 230))
        p.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        p.drawText(
            QRectF(cx - 120, cy - 20, 240, 40),
            Qt.AlignmentFlag.AlignCenter,
            "JARVIS"
        )

        p.setFont(QFont("Arial", 9))
        p.setPen(QColor(120, 220, 255, 180))
        p.drawText(
            QRectF(cx - 120, cy + 20, 240, 30),
            Qt.AlignmentFlag.AlignCenter,
            f"SYSTEM {self.state.upper()}"
        )


# ================= MAIN =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = JarvisWidget()
    w.show()
    sys.exit(app.exec())