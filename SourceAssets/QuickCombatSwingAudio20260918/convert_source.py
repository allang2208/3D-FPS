"""把用户提供的 quickhit2.mp3 转成工程惯用格式（44.1 kHz / 立体声 / 16-bit PCM WAV）。

与 SourceAssets/WeaponHitAudio20260916 同一口径：仓库只做格式转换与导入，不再分发原始 mp3。
"""
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

SRC = Path(r'D:\FPS3D\资产\音效\quickhit2.mp3')
OUT = Path(__file__).parent / 'S_QuickCombatSwing.wav'

if not SRC.exists():
    sys.exit('source missing: %s' % SRC)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
cmd = [ffmpeg, '-y', '-i', str(SRC), '-ar', '44100', '-ac', '2', '-c:a', 'pcm_s16le', str(OUT)]
print('[QCAUDIO] ' + ' '.join(cmd), flush=True)
subprocess.run(cmd, check=True)
print('[QCAUDIO] wrote %s (%d bytes)' % (OUT, OUT.stat().st_size), flush=True)
