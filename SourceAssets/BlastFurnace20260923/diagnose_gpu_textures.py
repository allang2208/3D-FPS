"""Read back what the MASKS-compressed textures actually contain on the GPU.

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash

The furnace renders as a grey-white checker in game, while the same PNGs read
correctly from disk. The difference has to live in the imported texture data,
so this draws each texture to a render target, reads the pixels back and
reports per-channel statistics. A texture whose GPU content is flat or zero is
a broken import, not a streaming problem.
"""
import json
import struct
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
OUT = HERE / 'gpu-readback'
OUT.mkdir(parents=True, exist_ok=True)
ROOT = '/Game/Props/BlastFurnace20260923'
SAMPLES = [
    'M_BlastFurnace_Firebrick',
    'M_BlastFurnace_Masonry',
    'M_BlastFurnace_WroughtIron',
]

report = {}
for name in SAMPLES:
    path = '%s/Materials/%s' % (ROOT, name)
    material = u.load_asset(path)
    if material is None:
        report[name] = {'loaded': False}
        continue
    width, height = 128, 128
    target = u.RenderingLibrary.create_render_target2d(
        None, width, height, u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    u.RenderingLibrary.clear_render_target2d(None, target, u.LinearColor(0, 0, 0, 1))
    # Draw the material itself: this is exactly what the mesh samples in game,
    # so a checker or flat result here reproduces the white-model look.
    u.RenderingLibrary.draw_material_to_render_target(None, target, material)
    # Export to disk and measure with PIL. export_render_target writes a file
    # with no extension (project note, 2026-09-18), so it is renamed here.
    raw = OUT / (name + '.raw')
    u.RenderingLibrary.export_render_target(None, target, str(OUT), name)
    produced = OUT / name
    if produced.exists():
        produced.rename(raw)
    if not raw.exists():
        report[name] = {'exported': False}
        continue
    from PIL import Image
    with Image.open(raw) as image:
        converted = image.convert('RGBA')
        size = converted.size
        data = converted.tobytes()
    raw.unlink()
    # No numpy inside UE's interpreter: unpack the raw bytes by channel.
    count = size[0] * size[1]
    entry = {'exported': True, 'size': list(size)}
    for index, channel in enumerate('RGBA'):
        values = [data[i] / 255.0 for i in range(index, len(data), 4)]
        entry[channel] = {'mean': round(sum(values) / len(values), 4),
                          'min': round(min(values), 4),
                          'max': round(max(values), 4)}
    report[name] = entry
    print('GPU_READBACK %-32s %s' % (name, json.dumps(entry, ensure_ascii=False)), flush=True)
    # Read the pixels straight back out of the GPU: no disk round trip, so the
    # numbers describe what the material sampler would actually see.
    raw = u.RenderingLibrary.read_render_target_raw_pixel_area(
        None, target, u.IntRect(0, 0, width, height))
    flat = [float(c) for channel in raw for c in channel] if raw and len(raw) else []
    entry = {'sampled': len(flat) // 4}
    if flat:
        for index, channel in enumerate('RGBA'):
            values = flat[index::4]
            entry[channel] = {'mean': round(sum(values) / len(values), 4),
                              'min': round(min(values), 4), 'max': round(max(values), 4)}
    report[name] = entry
    print('GPU_READBACK %-42s %s' % (name, json.dumps(entry, ensure_ascii=False)), flush=True)

(HERE / 'gpu-readback.json').write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                        encoding='utf-8')
print('GPU_READBACK_DONE', flush=True)
