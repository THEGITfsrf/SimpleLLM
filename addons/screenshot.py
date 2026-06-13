import os
import time
import io
import base64

import pyautogui
from PIL import Image

description = "Takes a screenshot of the user's screen and returns the image. Used for seeing what they see."

args = {
    "out_path": {
        "type": "string",
        "description": "Optional output image path"
    },
    "max_width": {
        "type": "integer",
        "description": "Maximum image width before resizing"
    },
    "grayscale": {
        "type": "boolean",
        "description": "Convert screenshot to grayscale to reduce size"
    }
}

required = []


def main(
    out_path=None,
    max_width=1024,
    grayscale=True
):
    try:
        # 📁 default output folder
        if out_path is None:
            folder = "./images"
            os.makedirs(folder, exist_ok=True)

            out_path = os.path.join(
                folder,
                f"screenshot_{int(time.time())}.png"
            )

        # make absolute path
        out_path = os.path.abspath(out_path)

        # ensure folder exists
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # 📸 capture screenshot
        img = pyautogui.screenshot()

        # ⚫ grayscale reduces filesize/token usage
        if grayscale:
            img = img.convert("L")

        # 🔻 smart resize
        if img.width > max_width:
            ratio = max_width / img.width

            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)

            img = img.resize(
                (new_width, new_height),
                Image.LANCZOS
            )

        # 💾 save as PNG for text clarity
        img.save(
            out_path,
            format="PNG",
            optimize=True
        )

        # 🧬 encode for optional inline model usage
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)

        return {
            "status": "ok",
            "path": out_path,
            "width": img.width,
            "height": img.height,
            "grayscale": grayscale,
            "image": base64.b64encode(buf.getvalue()).decode("utf-8")
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }