"""Download the reference and extract the standing hold frames (frame index = file seconds x 30).

python -I Reference/extract_idle.py
Writes Saved/Reference/DualKukriBV19dUqBJECT20261025/{info.info.json, ref_1080.mp4, idle_frames/fNNNNN.png,
sheets/sheet_0_8.jpg}.  The video (Bilibili BV19dUqBJECT, Apex 通用传家宝 绝命二重奏, 1080p30 avc) stays local.
"""
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

OUT = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\DualKukriBV19dUqBJECT20261025")
URL = "https://www.bilibili.com/video/BV19dUqBJECT/"
FF = imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd):
    print(' '.join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, cwd=OUT)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not (OUT / 'ref_1080.mp4').exists():
        run([sys.executable, '-m', 'yt_dlp', '--write-info-json', '-o', 'info.%(ext)s', '--skip-download', URL])
        run([sys.executable, '-m', 'yt_dlp', '-f', '30080', '-o', 'ref_1080.%(ext)s', URL])
    (OUT / 'sheets').mkdir(exist_ok=True)
    (OUT / 'idle_frames').mkdir(exist_ok=True)
    # Chapter 握持姿势 0-40 s: title card to ~1.9 s, standing hold 2.0-4.15 s, then crouch.
    run([FF, '-v', 'error', '-y', '-ss', '0', '-t', '8', '-i', 'ref_1080.mp4', '-vf', 'fps=4,scale=480:-1,tile=4x8',
         '-frames:v', '1', 'sheets/sheet_0_8.jpg'])
    run([FF, '-v', 'error', '-y', '-ss', '1.9', '-t', '2.5', '-i', 'ref_1080.mp4', '-vsync', '0', '-start_number', '57',
         'idle_frames/f%05d.png'])


if __name__ == '__main__':
    main()
