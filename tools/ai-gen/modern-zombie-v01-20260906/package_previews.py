from pathlib import Path
import json, math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
report = json.loads((ROOT / 'build-report.json').read_text())
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
out = ROOT / 'previews'
out.mkdir(exist_ok=True)
checks = {}
for clip in ('Idle', 'Walk', 'Attack', 'AttackRight', 'Death', 'HitReact'):
    seconds = report['clips'][clip]
    files = sorted((ROOT / 'rendered' / 'modern' / clip).glob('[0-9][0-9][0-9].png'))
    count = math.ceil(seconds * 24 - 1e-6)
    frames = [Image.open(p).convert('RGB').resize((600, 540), Image.Resampling.LANCZOS) for p in files[:count]]
    times = [round(min(i / 24, seconds) * 100) * 10 for i in range(count + 1)]
    durations = [times[i+1] - times[i] for i in range(count)]
    target = out / f'{clip}.gif'
    frames[0].save(target, save_all=True, append_images=frames[1:], duration=durations, loop=0, disposal=2, optimize=False)
    with Image.open(target) as gif:
        actual_ms = 0
        for i in range(gif.n_frames):
            gif.seek(i)
            actual_ms += gif.info['duration']
        checks[clip] = {'source_frames': count, 'gif_frames': gif.n_frames, 'source_seconds': seconds, 'gif_seconds': actual_ms / 1000}
        assert gif.n_frames == count and abs(actual_ms / 1000 - seconds) <= .005
    sheet = Image.new('RGB', (1200, 894), '#18212b')
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 9), f'{clip}  /  {seconds:.3f}s  /  actual Godot model', font=font, fill='white')
    for j in range(12):
        i = round(j * (len(files) - 1) / 11)
        frame = Image.open(files[i]).convert('RGB').resize((300, 270), Image.Resampling.LANCZOS)
        x, y = (j % 4) * 300, 45 + (j // 4) * 283
        sheet.paste(frame, (x, y))
        draw.text((x+8, y+5), f'{min(i/24, seconds):.2f}s', font=small, fill='white')
    sheet.save(out / f'{clip}-contact.jpg', quality=91)

comparison = Image.new('RGB', (1800, 585), '#18212b')
draw = ImageDraw.Draw(comparison)
for j, (version, title) in enumerate((('previous', 'Previous game model'), ('A', 'Denys original asset'), ('modern', 'Modern zombie V01'))):
    frame = Image.open(ROOT / 'rendered' / version / 'front.png').convert('RGB').resize((600, 540), Image.Resampling.LANCZOS)
    comparison.paste(frame, (j * 600, 45))
    draw.text((j * 600 + 18, 10), title, font=font, fill='white')
comparison.save(out / 'comparison.jpg', quality=93)
(out / 'preview-validation.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
print(json.dumps(checks, indent=2))
