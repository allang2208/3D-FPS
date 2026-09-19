"""Assemble same-process screenshots and mixer audio on their actual wall clock."""
from pathlib import Path
from datetime import datetime
import json
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
run = root / 'Saved/ReloadTiming' / ('ColdSteel_' + sys.argv[1])
ff = root / 'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
log = (run / 'runtime.log').read_text(encoding='utf-8-sig', errors='replace')
stamp = r'\[(\d{4}\.\d\d\.\d\d-\d\d\.\d\d\.\d\d:\d{3})\]'
def seconds(text):
    return datetime.strptime(text, '%Y.%m.%d-%H.%M.%S:%f').timestamp()
origin = seconds(re.search(stamp + r'.*RELOAD_TIMING_AUDIO_START', log)[1])
frames = {}
for m in re.finditer(stamp + r'.*RELOAD_TIMING_FRAME name=(case(\d+)_\S+) world=([\d.]+) elapsed=([\d.]+)', log):
    if (run / m[2]).exists():
        frames.setdefault(int(m[3]), []).append((seconds(m[1]) - origin, m[2], float(m[5])))
report = {'clock': 'Original screenshot wall timestamps with the same process mixer; one common recording origin, no individual audio-event shifts.', 'segments': []}
segments = []
for case in (0, 1, 15, 16, 21, 22):
    sequence = frames[case]
    # More than one request in a frame can replace an earlier screenshot.
    sequence = sorted({name: (t, name, elapsed) for t, name, elapsed in sequence}.values())
    lines = ['ffconcat version 1.0']
    gaps = []
    for i, (t, name, _) in enumerate(sequence):
        gap = max(.001, sequence[i + 1][0] - t) if i + 1 < len(sequence) else .08
        gaps.append(gap)
        lines += [f"file '{name}'", f'duration {gap:.6f}']
    lines += [f"file '{sequence[-1][1]}'"]
    concat = run / f'case{case:02d}.ffconcat'
    concat.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    info = re.search(rf'RELOAD_TIMING START case={case} weapon=(\w+) drum=(\d) empty=(\d) duration_mult=([\d.]+) duration=([\d.]+)', log)
    label = f'{info[1]} {"drum" if info[2] == "1" else "standard"} {"empty" if info[3] == "1" else "normal"} | {float(info[5]):.3f}s | speed {1/float(info[4]):.2f}x'
    out = run / f'case{case:02d}.mp4'
    subprocess.run([str(ff), '-y', '-loglevel', 'error', '-safe', '0', '-i', str(concat),
        '-ss', str(max(0, sequence[0][0])), '-i', str(run / 'mix.wav'),
        '-t', str(sum(gaps)), '-vf', f"drawbox=x=0:y=0:w=iw:h=36:color=black@0.8:t=fill,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='{label}':fontcolor=white:fontsize=20:x=12:y=8",
        '-r', '30', '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', str(out)], check=True)
    segments.append(out)
    report['segments'].append({'case': case, 'label': label, 'frames': len(sequence), 'largest_capture_gap': max(gaps), 'duration': sum(gaps), 'video': str(out)})
listing = run / 'preview.ffconcat'
listing.write_text('ffconcat version 1.0\n' + ''.join(f"file '{p.name}'\n" for p in segments), encoding='utf-8')
subprocess.run([str(ff), '-y', '-loglevel', 'error', '-safe', '0', '-i', str(listing), '-c', 'copy', '-movflags', '+faststart', str(run / 'reload-speed-preview.mp4')], check=True)
(run / 'preview.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
