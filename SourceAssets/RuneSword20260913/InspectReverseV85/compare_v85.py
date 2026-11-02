"""Reference keys (played in reverse) vs V85 at the same keys: brightened reference hand crop / V85 hand close-up /
V85 viewmodel-camera crop.

py compare_v85.py <view dir> <hand dir> <out.jpg>   (render dirs from render_review.py with --frames=<key frames>)
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

P = Path(__file__).parent
REF = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\RuneSwordSpinBV1hCJFzQEyR20261030\frames")
# reference hand crops (x0, y0, x1, y1) per frame
CROP = {2288: (1350, 250, 1920, 1000), 2287: (1350, 300, 1920, 1030), 2286: (1350, 300, 1920, 1030),
        2285: (1400, 300, 1920, 1030), 2284: (1400, 350, 1920, 1080), 2283: (1450, 250, 1920, 1000),
        2282: (1450, 300, 1920, 1080), 2281: (1450, 250, 1920, 1000), 2280: (1350, 250, 1920, 1000)}
W, H = 300, 380


def tile(im, text):
    im = im.convert('RGB')
    im = ImageOps.fit(im, (W, H), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle((0, H - 28, W, H), fill=(0, 0, 0))
    d.text((5, H - 26), text, font=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16), fill=(255, 255, 0))
    return im


def main():
    view, hand, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    keys = json.loads((P / 'keys_v85.json').read_text(encoding='utf-8'))['keys']
    sheet = Image.new('RGB', (W * len(keys), H * 3), (20, 20, 20))
    have = sorted(int(p.stem[1:]) for p in hand.glob('f*.png'))
    for i, k in enumerate(keys):
        f = min(have, key=lambda n: abs(n - k['t'] * 120))
        r = Image.open(REF / f"f{k['ref']:05d}.png").crop(CROP[k['ref']])
        r = ImageOps.autocontrast(r.convert('RGB').point(lambda v: int(255 * (v / 255) ** 0.45)), cutoff=1)
        sheet.paste(tile(r, f"参考 {k['ref']} → {k['name']}"), (i * W, 0))
        sheet.paste(tile(Image.open(hand / f'f{f:04d}.png'), f"V85 {k['name']} {k['t']:.3f}s 手部"), (i * W, H))
        sheet.paste(tile(Image.open(view / f'f{f:04d}.png').crop((520, 60, 960, 540)), f"V85 视角 φ{k['phi']}"),
                    (i * W, 2 * H))
    sheet.save(P / out, quality=90)
    print(out, sheet.size)


if __name__ == '__main__':
    main()
