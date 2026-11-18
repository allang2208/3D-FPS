"""Assemble labeled male/female preview GIFs, MP4s and contact close-ups."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(os.environ.get('CHAPEL_PREVIEW_ROOT', 'D:/FPS3D/FPSGAME/SourceAssets/ChapelFurniture20261116/PreviewR1'))
candidate = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8-sig')).get('kind') == 'authored_candidate'
source_label = '动作调整稿' if candidate else '已保存原生动画'
FFMPEG = Path('D:/FPS3D/FPSGAME/SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')
FONT = 'C:/Windows/Fonts/msyh.ttc'
font = lambda size: ImageFont.truetype(FONT, size)
BG = (20, 25, 33)
INK = (232, 237, 244)
MUTED = (170, 184, 201)
labels = {'default': '男角色 · Jason', 'kaitlin': '女角色 · Kaitlin'}
phases = {'Enter': '坐下', 'Idle': '坐稳', 'Exit': '起身'}


def fit_image(path, size):
    im = Image.open(path).convert('RGB')
    im.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new('RGB', size, BG)
    canvas.paste(im, ((size[0] - im.width)//2, (size[1] - im.height)//2))
    return canvas


board = Image.new('RGB', (1600, 1300), BG)
d = ImageDraw.Draw(board)
d.text((28, 15), '教堂长椅 · 坐稳接触特写', font=font(34), fill=INK)
d.text((30, 64), source_label + ' + 实际模型尺寸｜中性灰模｜剖切仅隐藏近侧椅体', font=font(20), fill=MUTED)
for row, (variant, label) in enumerate(labels.items()):
    top = 110 + row * 590
    d.text((28, top), label, font=font(27), fill=INK)
    hand_title = '自然下垂手掌与椅面' if os.environ.get('CHAPEL_PREVIEW_HANGING') == '1' else '手掌与大腿'
    for col, (view, title) in enumerate((('seat', '臀部与椅面（侧面剖切）'), ('feet', '双脚与地面'), ('palms', hand_title))):
        x = 24 + col * 524
        board.paste(fit_image(ROOT / variant / (view + '.png'), (512, 500)), (x, top + 75))
        d.text((x + 12, top + 43), title, font=font(22), fill=MUTED)
board.save(ROOT / 'chapel_pew_contacts.png')

overview = Image.new('RGB', (1280, 780), BG)
od = ImageDraw.Draw(overview)
for i, (variant, label) in enumerate(labels.items()):
    overview.paste(Image.open(ROOT / variant / 'overview.png').convert('RGB'), (640*i, 64))
    od.text((24+640*i, 15), label + ' · 坐稳', font=font(28), fill=INK)
overview.save(ROOT / 'chapel_pew_overview.png')
if os.environ.get('CHAPEL_PREVIEW_HANDS') == '1':
    previous = Path(os.environ.get('CHAPEL_PREVIEW_PREVIOUS', str(ROOT.parents[1] / 'PreviewR1')))
    if all((previous / variant / 'palms.png').is_file() for variant in labels):
        comparison = Image.new('RGB', (1280, 1110), BG)
        cd = ImageDraw.Draw(comparison)
        cd.text((24, 12), '教堂长椅 · 手部调整前后', font=font(32), fill=INK)
        cd.text((24, 55), '相同模型、坐稳时刻与机位｜' + source_label, font=font(20), fill=MUTED)
        for row, (variant, label) in enumerate(labels.items()):
            top = 100 + row * 500
            for column, (folder, version) in enumerate(((previous, '调整前'), (ROOT, '调整后'))):
                x = column * 640
                cd.text((x + 24, top), label + ' · ' + version, font=font(25), fill=INK)
                crop = Image.open(folder / variant / 'palms.png').convert('RGB').crop((0, 250, 640, 700))
                comparison.paste(crop, (x, top + 45))
        comparison.save(ROOT / 'chapel_pew_hands_before_after.png')
if '--stills' in sys.argv:
    print('CHAPEL_CONTACT_SHEET_COMPLETE')
    raise SystemExit(0)

for variant, label in labels.items():
    timeline = json.loads((ROOT / variant / 'timeline.json').read_text())
    destination = ROOT / variant / 'composite'
    destination.mkdir(exist_ok=True)
    for i, (phase, t) in enumerate(timeline):
        im = Image.new('RGB', (1280, 800), BG)
        im.paste(Image.open(ROOT / variant / 'overview' / f'{i:04d}.png').convert('RGB'), (0, 72))
        im.paste(Image.open(ROOT / variant / 'side' / f'{i:04d}.png').convert('RGB'), (640, 72))
        draw = ImageDraw.Draw(im)
        draw.text((22, 9), label + '  |  ' + phases[phase], font=font(28), fill=INK)
        draw.text((1000, 14), f'{t:.2f} 秒 · 原速', font=font(21), fill=MUTED)
        draw.text((22, 45), '完整长椅 · 前侧视角', font=font(20), fill=MUTED)
        detail_label = '手臂与手掌近景' if os.environ.get('CHAPEL_PREVIEW_HANDS') == '1' else '侧面剖切 · 仅隐藏近侧椅体'
        draw.text((662, 45), detail_label, font=font(20), fill=MUTED)
        draw.text((22, 772), source_label + '与实际蒙皮几何 · 接触预览 · 非游戏交互录像', font=font(18), fill=MUTED)
        im.save(destination / f'{i:04d}.png')
    stem = 'chapel_pew_' + ('male' if variant == 'default' else 'female')
    subprocess.run([str(FFMPEG), '-hide_banner', '-loglevel', 'error', '-y', '-framerate', '15',
                    '-i', str(destination / '%04d.png'), '-c:v', 'libx264', '-crf', '18',
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(ROOT / (stem + '.mp4'))], check=True)
    subprocess.run([str(FFMPEG), '-hide_banner', '-loglevel', 'error', '-y', '-framerate', '15',
                    '-i', str(destination / '%04d.png'), '-vf',
                    'fps=12,scale=960:600:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle',
                    '-loop', '0', str(ROOT / (stem + '_inline.gif'))], check=True)
    shutil.copy2(ROOT / (stem + '_inline.gif'), ROOT / (stem + '.gif'))
    print('CHAPEL_PREVIEW_ENCODED', variant, len(timeline), flush=True)
