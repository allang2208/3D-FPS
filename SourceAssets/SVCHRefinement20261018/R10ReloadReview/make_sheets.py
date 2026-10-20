import json, sys
from pathlib import Path
from PIL import Image, ImageDraw

P = Path(__file__).parents[3]
O = P / 'Saved/SVCHPoseAudit' / sys.argv[1]
rows = [json.loads(s) for s in (O / 'frames.jsonl').read_text(encoding='utf-8-sig').splitlines() if s.strip()]
for role in ('reload_normal', 'reload_empty'):
    selected = [r for r in rows if r['stage'] == role and r['action_alpha'] > .01]
    width, height = 640, 280
    sheet = Image.new('RGB', (width * 3, height * ((len(selected) + 2) // 3)), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)
    for i, r in enumerate(selected):
        img = Image.open(O / 'Frames' / r['image']).convert('RGB').crop((240, 350, 1200, 720))
        img.thumbnail((width, height - 25))
        x, y = (i % 3) * width, (i // 3) * height
        sheet.paste(img, (x, y + 25))
        draw.text((x + 6, y + 5), f"{r['image']} | source {r['action_time']:.3f}s", fill='white')
    sheet.save(O / (role + '_contact.jpg'), quality=93)
    print(O / (role + '_contact.jpg'))
