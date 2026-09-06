"""Assemble the 144 actual Godot-rendered frames; no generated or interpolated frames."""
from pathlib import Path
import argparse
from PIL import Image, GifImagePlugin
root = Path(__file__).parent
parser = argparse.ArgumentParser()
parser.add_argument('--source', default='felling-frames')
parser.add_argument('--output', default='tree-felling-preview.gif')
args = parser.parse_args()
paths = sorted((root / args.source).glob('*.png'))
assert len(paths) == 144
frames = []
for path in paths:
    with Image.open(path) as source:
        frame = source.convert('RGB')
        frame.thumbnail((960, 640), Image.Resampling.LANCZOS)
        frames.append(frame)
assert len({frame.size for frame in frames}) == 1
durations = [40, 40, 50, 40, 40, 40] * 24  # GIF centiseconds: exactly six seconds.
# Explicit frame writing prevents Pillow coalescing identical held poses.
palette_frames = [frame.quantize(colors=192) for frame in frames]
with (root / args.output).open('wb') as stream:
    for block in GifImagePlugin._get_global_header(palette_frames[0], {'loop': 0}):
        stream.write(block)
    for frame, duration in zip(palette_frames, durations):
        GifImagePlugin._write_frame_data(stream, frame, (0, 0),
            {'duration': duration, 'disposal': 2, 'include_color_table': True})
    stream.write(b';')
with Image.open(root / args.output) as result:
    assert result.n_frames == 144
    total = 0
    for index in range(result.n_frames):
        result.seek(index)
        total += result.info['duration']
    assert total == 6000
print(f'{args.output} PASS: 144 frames, 6000 ms, {frames[0].size}')
