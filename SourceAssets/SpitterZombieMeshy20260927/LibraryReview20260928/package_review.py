"""Package source animations for the requested motion-library review."""
import json, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'Preview'
OUT.mkdir(exist_ok=True)
FONT = 'C:/Windows/Fonts/msyh.ttc'
def font(size): return ImageFont.truetype(FONT, size)
rows = {r['name']: r for r in json.loads((ROOT / 'render_all.json').read_text())}
for extra in ROOT.glob('render_reframe*.json'):
    rows.update({r['name']: r for r in json.loads(extra.read_text())})
def frames(name):
    folder = ROOT / rows[name].get('folder', 'Frames/' + name)
    return sorted(folder.glob('*.png'))[:rows[name]['frames']]

def sheet(names, output):
    names = [n for n in names if n in rows]
    if not names: return
    im = Image.new('RGB', (8 * 192, len(names) * 272), '#161e25')
    draw = ImageDraw.Draw(im)
    for y, name in enumerate(names):
        row = rows[name]; files = frames(name)
        draw.text((10, y * 272 + 3), f"{name}  |  {row['seconds']:.2f}s  |  源动作，未重定向", font=font(18), fill='white')
        for j in range(8):
            k = round(j * (len(files) - 1) / 7)
            with Image.open(files[k]) as src:
                im.paste(src.resize((192, 224), Image.Resampling.LANCZOS), (j * 192, y * 272 + 28))
            draw.text((j * 192 + 6, y * 272 + 251), f"{row['times'][k]:.2f}s", font=font(15), fill='#b9cbd7')
    im.save(OUT / output)

def gif(names, output):
    if any(n not in rows or rows[n]['fps'] is None for n in names): return
    width, height = 320, 374
    # Display every sequence at original speed; shorter ones repeat independently.
    count = math.ceil(max(rows[n]['seconds'] for n in names) * 15)
    cache = {}
    for name in names:
        cache[name] = []
        for path in frames(name):
            with Image.open(path) as im:
                cache[name].append(im.convert('RGB').resize((width, height), Image.Resampling.LANCZOS))
    rendered = []
    for i in range(count):
        im = Image.new('RGB', (width * 2, (height + 54) * 2 + 30), '#141c23')
        d = ImageDraw.Draw(im)
        d.text((10, 5), '动作库原速预览 · UE5 源骨架 · 尚未重定向到毒液僵尸', font=font(16), fill='#d8e4ee')
        for p, name in enumerate(names):
            x, y = (p % 2) * width, 30 + (p // 2) * (height + 54)
            local = (i / 15) % rows[name]['seconds']
            k = min(int(local * 15 + 1e-5), len(cache[name]) - 1)
            im.paste(cache[name][k], (x, y + 54))
            d.text((x + 10, y + 5), name, font=font(22), fill='white')
            d.text((x + 10, y + 32), f"{local:.2f} / {rows[name]['seconds']:.2f} s  |  1×", font=font(15), fill='#b9cbd7')
        rendered.append(im)
    samples = Image.new('RGB', (640, rendered[0].height * 5))
    for i in range(5): samples.paste(rendered[round(i * (count - 1) / 4)], (0, i * rendered[0].height))
    palette = samples.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    converted = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in rendered]
    converted[0].save(OUT / output, save_all=True, append_images=converted[1:], loop=0,
                      duration=[70 if i % 3 != 2 else 60 for i in range(count)], disposal=2)

attacks = ['anim_Attack_' + n for n in 'ABCD']
locomotion = ['anim_Walk_' + n for n in 'ABC'] + ['anim_Run_A']
sheet(attacks, 'Attack_Source_ContactSheet.png')
sheet(locomotion, 'Locomotion_Source_ContactSheet.png')
sheet(['anim_Idle_A', 'anim_Idle_B'], 'Idle_Source_ContactSheet.png')
sheet(['anim_Burst_' + n for n in 'ABCDE'], 'Burst_A_E_ContactSheet.png')
sheet(['anim_Burst_' + n for n in 'FGHIK'], 'Burst_F_K_ContactSheet.png')
gif(attacks, 'Attack_Source_Comparison.gif')
gif(locomotion, 'Locomotion_Source_Comparison.gif')
print('Packaged review:', OUT)
