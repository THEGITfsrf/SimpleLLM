import os
import torch
from PIL import Image
from diffusers import FluxKontextPipeline

# -----------------------------
# CONFIG
# -----------------------------

CUDA_DEVICE = 1
INPUT_LOGO = "aura_logo.png"
OUT_DIR = "outputs"
os.makedirs(OUT_DIR, exist_ok=True)

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

print("Using:", torch.cuda.get_device_name(CUDA_DEVICE))

# -----------------------------
# LOAD MODEL (SAFE MODE)
# -----------------------------

pipe = FluxKontextPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-Kontext-dev",
    torch_dtype=torch.float16,
    device_map="balanced",   # 🔥 KEY FIX
)

# memory safety tools
pipe.enable_model_cpu_offload()
pipe.enable_attention_slicing()
pipe.vae.enable_slicing()
pipe.vae.enable_tiling()

# DO NOT manually move model to cuda

# -----------------------------
# INPUT
# -----------------------------

logo = Image.open(INPUT_LOGO).convert("RGB")
logo = logo.resize((768, 768))

CORE_IDENTITY = """
Golden Energy Core aesthetic.
Black armor with glowing gold cracks.
Contained unstable power.
"""

NEGATIVE = "blurry, watermark, text, low quality, bad anatomy"

PROMPTS = {
    "face": CORE_IDENTITY + "Roblox avatar face icon glowing gold eyes.",
    "tshirt": CORE_IDENTITY + "Roblox T-shirt emblem centered.",
    "shirt": CORE_IDENTITY + "Black hoodie armor energy seams.",
    "pants": CORE_IDENTITY + "Futuristic black pants gold fractures."
}

# -----------------------------
# GENERATE
# -----------------------------

for name, prompt in PROMPTS.items():

    print(f"Generating {name}...")

    with torch.inference_mode():
        image = pipe(
            image=logo,
            prompt=prompt,
            negative_prompt=NEGATIVE,
            width=768,
            height=768,
            guidance_scale=2.5,
            num_inference_steps=20,
            generator=torch.Generator(device=f"cuda:{CUDA_DEVICE}").manual_seed(42),
        ).images[0]

    path = os.path.join(OUT_DIR, f"{name}.png")
    image.save(path)

    print("Saved:", path)

torch.cuda.empty_cache()

print("Done.")