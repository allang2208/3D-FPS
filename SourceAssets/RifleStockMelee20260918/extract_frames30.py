"""按 30 fps 原帧抽取参考视频 63.0–68.5 s（AK47 枪托近战段），供逐帧读谱。

输出 Reference/f30/f_XXXX.png（XXXX = 帧号，对应时间 = 63.0 + (N-1)/30）。
"""
import subprocess
from pathlib import Path

import imageio_ffmpeg

DIR = Path(__file__).resolve().parent
SRC = Path(r'D:\FPS3D\test\uzi_ref\uzi_ref.mp4')
OUT = DIR / 'Reference' / 'f30'
OUT.mkdir(parents=True, exist_ok=True)

for old in OUT.glob('f_*.png'):
    old.unlink()

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ffmpeg, '-v', 'error', '-y', '-ss', '63.0', '-to', '68.5', '-i', str(SRC),
                '-vf', 'fps=30', str(OUT / 'f_%04d.png')], check=True)

frames = sorted(OUT.glob('f_*.png'))
print('frames=%d first=%s last=%s' % (len(frames), frames[0].name, frames[-1].name))
