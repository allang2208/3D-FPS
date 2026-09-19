"""Read-only contact sheet of actual captured game frames for pose review."""
from pathlib import Path
from PIL import Image, ImageDraw

root = Path('D:/FPS3D/FPSGAME/Saved/GunplayUpgrade/m4-rig-final-dx12-60')
frames = [28, 32, 36, 40, 44, 48, 52, 56, 64, 69, 74, 79, 84, 89, 94, 99]
sheet = Image.new('RGB', (1920, 1200), (20, 24, 28))
draw = ImageDraw.Draw(sheet)
for index, frame in enumerate(frames):
    source = root / 'Frames' / f'Frame_{frame:04d}.png'
    with Image.open(source) as im:
        thumb = im.convert('RGB').resize((480, 270), Image.Resampling.LANCZOS)
    x, y = index % 4 * 480, index // 4 * 300
    sheet.paste(thumb, (x, y + 25))
    draw.text((x + 8, y + 6), f'{"Normal" if index < 8 else "Empty"} reload | audit t={2.8 + frame / 10:.1f}s', fill='white')
sheet.save(root / 'Preview' / 'reload_contact_sheet.png')
