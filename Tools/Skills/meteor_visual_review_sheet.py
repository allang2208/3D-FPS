"""Arrange actual UE offscreen frames for review without altering their exposure."""
from pathlib import Path
import argparse
from PIL import Image, ImageDraw

p = argparse.ArgumentParser()
p.add_argument('folder', type=Path)
p.add_argument('--impact-only', action='store_true')
args = p.parse_args()
indices = ([0, 2, 4, 8, 14, 23, 35, 50, 70, 95, 120, 149] if args.impact_only
           else [38, 40, 43, 47, 52, 59, 68, 80, 98, 120, 150, 179])
prefix = 'impact' if args.impact_only else 'frame'
sheet = Image.new('RGB', (960, 6 * 294), '#151719')
draw = ImageDraw.Draw(sheet)
for slot, frame in enumerate(indices):
    image = Image.open(args.folder / f'{prefix}-{frame:04d}.png').convert('RGB')
    image.thumbnail((480, 270))
    x, y = (slot % 2) * 480, (slot // 2) * 294
    sheet.paste(image, (x, y + 24))
    age = (frame + 1) / 60 - (0 if args.impact_only else .65)
    draw.text((x + 8, y + 5), f'impact {age:+.3f}s', fill='white')
sheet.save(args.folder / 'contact-sheet.jpg', quality=94)
frames = [Image.open(args.folder / f'{prefix}-{i:04d}.png').convert('RGB').resize((768, 432))
          for i in range(0, 150 if args.impact_only else 180, 2)]
name = 'meteor-impact.gif' if args.impact_only else 'meteor-actual-actor.gif'
frames[0].save(args.folder / name, save_all=True,
               append_images=frames[1:], duration=[33, 34, 33] * (len(frames) // 3), loop=0, optimize=False)
print(args.folder / 'contact-sheet.jpg')
