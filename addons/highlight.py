import threading

description = "Shows a temporary highlight circle on screen (default 5 seconds)."
args = {
    "x": {"type": "integer", "description": "Circle center X in screen pixels"},
    "y": {"type": "integer", "description": "Circle center Y in screen pixels"},
    "radius": {"type": "integer", "description": "Circle radius in pixels"},
    "duration_seconds": {"type": "number", "description": "How long to show the circle"},
}
required = []


def _run_overlay(x, y, radius, duration_seconds):
    import tkinter as tk

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="magenta")
    try:
        root.attributes("-transparentcolor", "magenta")
    except Exception:
        pass

    size = radius * 2 + 12
    left = int(x - size / 2)
    top = int(y - size / 2)
    root.geometry(f"{size}x{size}+{left}+{top}")

    canvas = tk.Canvas(root, width=size, height=size, bg="magenta", highlightthickness=0)
    canvas.pack()
    pad = 6
    canvas.create_oval(
        pad,
        pad,
        size - pad,
        size - pad,
        outline="red",
        width=5,
    )

    root.after(int(max(0.1, float(duration_seconds)) * 1000), root.destroy)
    root.mainloop()


def main(x=500, y=300, radius=70, duration_seconds=5):
    try:
        t = threading.Thread(
            target=_run_overlay,
            args=(int(x), int(y), max(10, int(radius)), max(0.1, float(duration_seconds))),
            daemon=True,
        )
        t.start()
        return {
            "status": "ok",
            "message": "Highlight started",
            "x": int(x),
            "y": int(y),
            "radius": max(10, int(radius)),
            "duration_seconds": max(0.1, float(duration_seconds)),
        }
    except Exception as e:
        return {"status": "error", "error": f"highlight failed: {e}"}
