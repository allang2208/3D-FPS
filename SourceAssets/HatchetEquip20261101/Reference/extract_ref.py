"""Download the hatchet draw reference and extract the toss-and-catch frames (frame index = file seconds x fps).

python -I Reference/extract_ref.py [start end]
Reference: Bilibili BV1pqkyYyEDY (user 2026-11-02: "39-40 s 的抛出接住").  Writes
Saved/Reference/HatchetBV1pqkyYyEDY20261102/{info.info.json, ref.mp4, frames/fNNNNN.png, sheets/}; the video stays local.
"""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

OUT = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\HatchetBV1pqkyYyEDY20261102")
URL = "https://www.bilibili.com/video/BV1pqkyYyEDY/"
FF = imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd):
    print(' '.join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, cwd=OUT)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not (OUT / 'info.info.json').exists():
        run([sys.executable, '-m', 'yt_dlp', '--write-info-json', '-o', 'info.%(ext)s', '--skip-download', URL])
    info = json.loads((OUT / 'info.info.json').read_text('utf-8'))
    if not (OUT / 'ref.mp4').exists():
        # best avc video at <= 1080p (no audio needed for the motion read)
        vids = [f for f in info['formats'] if f.get('vcodec', 'none').startswith('avc') and (f.get('height') or 0) <= 1080]
        best = max(vids, key=lambda f: (f.get('height') or 0, f.get('tbr') or 0))
        run([sys.executable, '-m', 'yt_dlp', '-f', best['format_id'], '-o', 'ref.%(ext)s', URL])
    t0, t1 = (float(v) for v in sys.argv[1:3]) if len(sys.argv) > 2 else (36.0, 43.0)
    fps = round(float(next(f for f in info['formats'] if f.get('vcodec', 'none') != 'none').get('fps') or 30))
    (OUT / 'sheets').mkdir(exist_ok=True)
    (OUT / 'frames').mkdir(exist_ok=True)
    run([FF, '-v', 'error', '-y', '-ss', str(t0), '-t', str(t1 - t0), '-i', 'ref.mp4', '-vf', 'fps=4,scale=480:-1,tile=4x7',
         '-frames:v', '1', 'sheets/overview_%d_%d.jpg' % (t0, t1)])
    run([FF, '-v', 'error', '-y', '-ss', str(t0), '-t', str(t1 - t0), '-i', 'ref.mp4', '-vsync', '0',
         '-start_number', str(int(round(t0 * fps))), 'frames/f%05d.png'])
    print('fps', fps, 'duration', info.get('duration'), 'title', info.get('title'))


if __name__ == '__main__':
    main()
