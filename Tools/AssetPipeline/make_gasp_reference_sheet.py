"""Assemble actual model renders; this is a source reference, not FPS acceptance."""
from pathlib import Path
from PIL import Image, ImageDraw

root = Path("D:/FPS3D/FPSGAME/SourceAssets/GASPTraversal20260910/Reference")
sheet = Image.new("RGB", (1920, 800), (24, 27, 32))
draw = ImageDraw.Draw(sheet)
for row, (name, frames) in enumerate((("Vault", (4, 8, 11, 18)), ("Mantle", (10, 18, 27, 36)))):
    for col, frame in enumerate(frames):
        tile = Image.open(root / f"{name}_{frame}.png").convert("RGB")
        sheet.paste(tile, (col * 480, row * 400 + 35))
        draw.text((col * 480 + 12, row * 400 + 10), f"Official {name} | exported frame {frame} | 30 fps", fill="white")
sheet.save(root / "official_motion_reference.jpg", quality=92)
