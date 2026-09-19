"""Summarize evaluated UE sprint samples and export the real 30 Hz capture."""
import bisect
import csv
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont

root = Path(sys.argv[1])
rows = [[float(x) for x in row] for row in csv.reader((root / 'sprint_samples.csv').open())]
steady = [row for row in rows if 18.0 <= row[0] < 19.85]
span = lambda column: max(r[column] for r in steady) - min(r[column] for r in steady)
grip_drift = max(math.dist(r[7:10], steady[0][7:10]) for r in steady)
report = {
    'samples': len(rows), 'steady_samples': len(steady),
    'muzzle_elevation_degrees': [min(r[6] for r in steady), max(r[6] for r in steady)],
    'lateral_travel_cm': span(4), 'vertical_travel_cm': span(5),
    'support_hand_receiver_relative_drift_cm': grip_drift,
    'minimum_steady_sprint_alpha': min(r[1] for r in steady),
    'note': 'Evaluated game sockets and viewmodel transform, fixed simulation rate; not measured rendering FPS.'
}
report['pass'] = (len(steady) >= 40 and 25 < report['muzzle_elevation_degrees'][0]
                  and report['muzzle_elevation_degrees'][1] < 50
                  and 3.0 < span(4) < 4.1 and span(5) < 1.2 and grip_drift < 0.02)
(root / 'sprint_validation.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))

if '--video' in sys.argv:
    out = root / 'Preview'
    out.mkdir(exist_ok=True)
    frames = {int(p.stem.split('_')[1]): p for p in (root / 'Frames').glob('Frame_*.png')}
    indices = sorted(frames)
    ffmpeg = 'D:/FPS3D/FPSGAME/SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
    # 16.6..20.35 includes entry, three seconds of running and the return to ADS.
    with tempfile.TemporaryDirectory(prefix='m4-sprint-', dir=out) as temp:
        for n, i in enumerate(range(414, 527)):
            source = frames[indices[max(0, bisect.bisect_right(indices, i) - 1)]]
            Path(temp, f'{n:04d}.png').hardlink_to(source)
        subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-framerate', '30', '-i', str(Path(temp, '%04d.png')),
                        '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out / 'sprint_preview.mp4')], check=True)
        subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-framerate', '30', '-i', str(Path(temp, '%04d.png')),
                        '-vf', 'fps=15,scale=768:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse',
                        str(out / 'sprint_preview.gif')], check=True)
    old = Path('D:/FPS3D/FPSGAME/Saved/GunplayUpgrade/m4-finger-final60/Frames/Frame_0123.png')
    canvas = Image.new('RGB', (1280, 400), '#12171f')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 21)
    for x, path, title in [(0, old, '原奔跑姿态'), (640, frames[480], '优化后：抬枪、双手握持')]:
        canvas.paste(Image.open(path).convert('RGB').resize((640, 360)), (x, 40))
        draw.text((x + 16, 7), title, font=font, fill='white')
    canvas.save(out / 'sprint_comparison.png')

if not report['pass']:
    raise SystemExit('Sprint pose validation failed')
