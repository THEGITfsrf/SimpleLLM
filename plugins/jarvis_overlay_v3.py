"""
JARVIS-style transparent HUD overlay for PyQt6.

Modes:
    MODE_IDLE     (1): cyan, fully static, 0.45 opacity (low-power look)
    MODE_ACTIVE   (2): orange, fast spin on all rings
    MODE_THINKING (3): purple, slow ambient rotation

Toggle via:
    - overlay.toggle_mode() / overlay.set_mode(...)
    - Global Ctrl+J hotkey (pynput; not in Colab)
    - POSIX SIGUSR1 (Colab notebook button)
"""

from __future__ import annotations

import math
import signal
import sys
from typing import Optional
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QRadialGradient, QPainterPath, QPalette,
)
_TOGGLE_PENDING = {"flag": False}

class JarvisController:
    def __init__(self, overlay: "JarvisOverlay"):
        self.overlay = overlay

    def toggle(self):
        self.overlay.toggle_mode()

    def idle(self):
        self.overlay.set_mode(self.overlay.MODE_IDLE)

    def active(self):
        self.overlay.set_mode(self.overlay.MODE_ACTIVE)

    def thinking(self):
        self.overlay.set_mode(self.overlay.MODE_THINKING)
def _install_signal_toggle() -> None:
    if not hasattr(signal, "SIGUSR1"):
        return  # Windows
    def _handler(signum, frame):  # noqa: ARG001
        _TOGGLE_PENDING["flag"] = True
    signal.signal(signal.SIGUSR1, _handler)


from PyQt6.QtCore import (
    Qt, QTimer, QPointF, QRectF, pyqtSignal, QObject, pyqtSlot,
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QRadialGradient, QPainterPath,
)
from PyQt6.QtWidgets import QApplication, QWidget


class HotkeyBridge(QObject):
    toggle_requested = pyqtSignal()


def start_global_hotkey(bridge: HotkeyBridge) -> Optional[object]:
    try:
        from pynput import keyboard
    except ImportError:
        print("[jarvis] pynput not installed -> global hotkey disabled.")
        return None
    def on_activate():
        bridge.toggle_requested.emit()
    hotkey = keyboard.GlobalHotKeys({"<ctrl>+j": on_activate})
    hotkey.daemon = True
    hotkey.start()
    return hotkey


class JarvisOverlay(QWidget):
    MODE_IDLE = 1
    MODE_ACTIVE = 2
    MODE_THINKING = 3
    SIZE = 400

    CYAN = QColor(120, 215, 255)
    CYAN_DIM = QColor(80, 170, 220)
    CYAN_DEEP = QColor(40, 110, 170)
    ORANGE = QColor(255, 150, 40)
    ORANGE_DIM = QColor(220, 110, 30)
    ORANGE_DEEP = QColor(160, 70, 20)
    PURPLE = QColor(190, 120, 255)
    PURPLE_DIM = QColor(150, 80, 220)
    PURPLE_DEEP = QColor(90, 40, 150)

    MODE_LABELS = {
        MODE_IDLE: "SYSTEM IDLE",
        MODE_ACTIVE: "SYSTEM LISTENING",
        MODE_THINKING: "SYSTEM THINKING",
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint

            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput

            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0, 0))
        self.setPalette(palette)
        self.setFixedSize(self.SIZE, self.SIZE)

        self._mode = self.MODE_IDLE
        self._angle_slow = 0.0
        self._angle_mid = 0.0
        self._angle_inner = 0.0
        self._angle_ticks = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    @pyqtSlot()
    def toggle_mode(self) -> None:
        next_mode = {
            self.MODE_IDLE: self.MODE_ACTIVE,
            self.MODE_ACTIVE: self.MODE_THINKING,
            self.MODE_THINKING: self.MODE_IDLE,
        }[self._mode]
        self.set_mode(next_mode)

    def set_mode(self, mode: int) -> None:
        if mode not in (self.MODE_IDLE, self.MODE_ACTIVE, self.MODE_THINKING):
            raise ValueError(f"Unknown mode: {mode}")
        self._mode = mode
        self.update()

    def get_mode(self) -> int:
        return self._mode

    def _tick(self) -> None:
        if _TOGGLE_PENDING["flag"]:
            _TOGGLE_PENDING["flag"] = False
            self.toggle_mode()

        if self._mode == self.MODE_ACTIVE:
            self._angle_slow = (self._angle_slow + 2.5) % 360.0
            self._angle_mid = (self._angle_mid - 4.5) % 360.0
            self._angle_ticks = (self._angle_ticks + 3.0) % 360.0
            self._angle_inner = (self._angle_inner + 32.0) % 360.0
            self.update()
        elif self._mode == self.MODE_THINKING:
            self._angle_slow = (self._angle_slow + 0.4) % 360.0
            self._angle_mid = (self._angle_mid - 0.7) % 360.0
            self._angle_ticks = (self._angle_ticks + 0.2) % 360.0
            self._angle_inner = (self._angle_inner + 1.6) % 360.0
            self.update()
        # Idle: fully static, no repaint.
    
    def paintEvent(self, event) -> None:
        p = QPainter(self)
        
        # 1. Clear the entire rectangle context directly using the painter
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        # 2. Apply anti-aliasing hints smoothly 
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        p.translate(cx, cy)
        if self._mode == self.MODE_ACTIVE:
            c_main, c_dim, c_deep = self.ORANGE, self.ORANGE_DIM, self.ORANGE_DEEP
        elif self._mode == self.MODE_THINKING:
            c_main, c_dim, c_deep = self.PURPLE, self.PURPLE_DIM, self.PURPLE_DEEP
        else:
            c_main, c_dim, c_deep = self.CYAN, self.CYAN_DIM, self.CYAN_DEEP
            p.setOpacity(0.22)
        radius = min(cx, cy) - 6.0
        self._draw_background_glow(p, radius, c_main)
        self._draw_outer_dashed_ring(p, radius * 0.98, c_dim)
        self._draw_tick_band(p, radius * 0.86, c_main, c_dim)
        self._draw_blueprint_lines(p, radius * 0.78, c_deep)
        self._draw_middle_arc_ring(p, radius * 0.68, c_main, c_dim)
        self._draw_thick_inner_ring(p, radius * 0.50, c_main, c_dim)
        self._draw_core(p, radius * 0.32, c_main, c_dim, c_deep)
        self._draw_center_label(p, c_main, c_dim)

    def _draw_background_glow(self, p, r, color):
        grad = QRadialGradient(QPointF(0, 0), r * 1.05)
        glow = QColor(color); glow.setAlpha(55)
        grad.setColorAt(0.0, glow)
        mid = QColor(color); mid.setAlpha(18)
        grad.setColorAt(0.55, mid)
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(-r, -r, 2 * r, 2 * r))

    def _draw_outer_dashed_ring(self, p, r, color):
        p.save()
        p.rotate(self._angle_slow)
        pen = QPen(color); pen.setWidthF(1.2)
        pen.setStyle(Qt.PenStyle.CustomDashLine)
        pen.setDashPattern([2, 4])
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(-r, -r, 2 * r, 2 * r))
        faint = QColor(color); faint.setAlpha(110)
        p.setPen(QPen(faint, 0.8))
        rr = r - 6
        p.drawEllipse(QRectF(-rr, -rr, 2 * rr, 2 * rr))
        p.restore()

    def _draw_tick_band(self, p, r, c_main, c_dim):
        p.save()
        p.rotate(self._angle_ticks)
        for i in range(72):
            p.save()
            p.rotate(i * (360.0 / 72))
            long_tick = (i % 6 == 0)
            tick_len = 10 if long_tick else 5
            tick_color = c_main if long_tick else c_dim
            tpen = QPen(tick_color)
            tpen.setWidthF(1.3 if long_tick else 0.8)
            p.setPen(tpen)
            p.drawLine(QPointF(0, -r), QPointF(0, -r + tick_len))
            p.restore()
        p.restore()

    def _draw_blueprint_lines(self, p, r, c_deep):
        p.save()
        faint = QColor(c_deep); faint.setAlpha(90)
        pen = QPen(faint); pen.setWidthF(0.7)
        p.setPen(pen)
        p.drawLine(QPointF(-r, 0), QPointF(r, 0))
        p.drawLine(QPointF(0, -r), QPointF(0, r))
        for ang in (30, 60, 120, 150):
            rad = math.radians(ang)
            x, y = math.cos(rad) * r, math.sin(rad) * r
            p.drawLine(QPointF(-x, -y), QPointF(x, y))
        p.restore()

    def _draw_middle_arc_ring(self, p, r, c_main, c_dim):
        p.save()
        p.rotate(self._angle_mid)
        rect = QRectF(-r, -r, 2 * r, 2 * r)
        pen = QPen(c_dim); pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        for start, span in [(10, 70), (90, 70), (190, 50), (250, 60), (320, 30)]:
            p.drawArc(rect, start * 16, span * 16)
        accent_pen = QPen(c_main); accent_pen.setWidthF(2.2)
        p.setPen(accent_pen)
        p.drawArc(rect, 100 * 16, 20 * 16)
        p.drawArc(rect, 280 * 16, 25 * 16)
        p.restore()

    def _draw_thick_inner_ring(self, p, r, c_main, c_dim):
        p.save()
        p.rotate(self._angle_inner)
        thickness = 16.0
        outer = r
        inner = r - thickness
        outer_rect = QRectF(-outer, -outer, 2 * outer, 2 * outer)
        inner_rect = QRectF(-inner, -inner, 2 * inner, 2 * inner)
        path = QPainterPath()
        path.addEllipse(outer_rect)
        path.addEllipse(inner_rect)
        path.setFillRule(Qt.FillRule.OddEvenFill)
        glow = QColor(c_main); glow.setAlpha(70)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(-outer - 4, -outer - 4, 2 * (outer + 4), 2 * (outer + 4)))
        base = QColor(c_dim); base.setAlpha(170)
        p.setBrush(base)
        p.drawPath(path)
        p.setBrush(Qt.BrushStyle.NoBrush)
        seg_pen = QPen(c_main); seg_pen.setWidthF(thickness - 2)
        seg_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(seg_pen)
        mid_r = (outer + inner) / 2
        mid_rect = QRectF(-mid_r, -mid_r, 2 * mid_r, 2 * mid_r)
        p.drawArc(mid_rect, 20 * 16, 40 * 16)
        p.drawArc(mid_rect, 140 * 16, 40 * 16)
        p.drawArc(mid_rect, 260 * 16, 40 * 16)
        hl = QColor(255, 255, 255, 60)
        p.setPen(QPen(hl, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(-inner, -inner, 2 * inner, 2 * inner))
        p.restore()

    def _draw_core(self, p, r, c_main, c_dim, c_deep):
        grad = QRadialGradient(QPointF(0, 0), r)
        deep = QColor(c_deep); deep.setAlpha(120)
        grad.setColorAt(0.0, deep)
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(-r, -r, 2 * r, 2 * r))
        for rr in (r * 0.85, r * 0.6):
            ring = QColor(c_dim); ring.setAlpha(140)
            p.setPen(QPen(ring, 0.8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(-rr, -rr, 2 * rr, 2 * rr))

    def _draw_center_label(self, p, color, dim_color):
        font = QFont("Consolas", 14, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4.0)
        p.setFont(font)
        p.setPen(QPen(QColor(245, 245, 245)))
        rect = QRectF(-100, -18, 200, 24)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "JARVIS")

        sub_font = QFont("Consolas", 7, QFont.Weight.Bold)
        sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        p.setFont(sub_font)
        p.setPen(QPen(QColor(210, 215, 225)))
        sub_rect = QRectF(-100, 8, 200, 16)
        p.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, self.MODE_LABELS[self._mode])


def main() -> int:
    app = QApplication(sys.argv)
    _install_signal_toggle()
    import os
    print(f"[jarvis] pid={os.getpid()} (send SIGUSR1 to toggle mode)", flush=True)

    overlay = JarvisOverlay()
    screen = app.primaryScreen().availableGeometry()
    overlay.move(
        screen.right() - overlay.width() - 40,
        screen.bottom() - overlay.height() - 40
    )
    overlay.show()
    start_socket_control(overlay)
    import ctypes

    hwnd = int(overlay.winId())

    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWCP_DONOTROUND = 1

    ctypes.windll.dwmapi.DwmSetWindowAttribute(
        hwnd,
        DWMWA_WINDOW_CORNER_PREFERENCE,
        ctypes.byref(ctypes.c_int(DWMWCP_DONOTROUND)),
        ctypes.sizeof(ctypes.c_int)
    )
    bridge = HotkeyBridge()
    bridge.toggle_requested.connect(overlay.toggle_mode)
    listener = start_global_hotkey(bridge)
    app._jarvis_hotkey_listener = listener  # type: ignore[attr-defined]

    return app.exec()
def start():
    return main()
import socket
import threading
def start_socket_control(overlay: "JarvisOverlay"):
    def run():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 5055))
        s.listen()

        print("[jarvis] socket control running on 127.0.0.1:5055")

        while True:
            conn, _ = s.accept()
            try:
                data = conn.recv(1024).decode().strip().lower()

                if data == "toggle":
                    overlay.toggle_mode()

                elif data == "idle":
                    overlay.set_mode(overlay.MODE_IDLE)

                elif data == "active":
                    overlay.set_mode(overlay.MODE_ACTIVE)

                elif data == "thinking":
                    overlay.set_mode(overlay.MODE_THINKING)

                elif data.startswith("opacity "):
                    # optional future upgrade hook
                    pass

            except Exception as e:
                print("[jarvis] socket error:", e)

            conn.close()

    threading.Thread(target=run, daemon=True).start()
if __name__ == "__main__":
    sys.exit(main())
