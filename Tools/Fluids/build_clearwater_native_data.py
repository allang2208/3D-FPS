"""Pack existing Clearwater caustic frames and emit the native-water wave kernel.

Offline asset production only. Does not launch Unreal, render previews, or run tests.
The 48-component spectrum remains an approximation of the MIT Clearwater source.
"""
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'SourceAssets/ClearwaterWater20260926'
OUT = ROOT / 'SourceAssets/ClearwaterNative20260926'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wave_doc = json.loads((SOURCE / 'waves.json').read_text(encoding='utf-8'))
    waves = wave_doc['waves']
    # Constants keep the baked spectrum (including phase) out of the broken 48-vector
    # parameter path. Runtime artist controls and all shared interaction vectors remain.
    code = ['// Generated from Clearwater waves.json. Units: positions cm, k rad/m.',
            'float2 p = Position.xy * 0.01;', 'float h = 0; float2 slope = 0;']
    for w in waves:
        amp, k = w['amplitude'], w['k']
        if amp <= 0:
            continue
        kx, ky = k * w['dir'][0], k * w['dir'][1]
        # The 212 m / 192-quad plane has a finite vertex grid: short waves belong in the normal,
        # not in undersampled geometry. Both use the same time, direction and phase.
        t = min(1.0, max(0.0, (w['wavelength'] - 2.3) / 2.3))
        geometry = t * t * (3.0 - 2.0 * t)
        code += ['{',
                 f' float ph = dot(p,float2({kx:.10f},{ky:.10f}))'
                 f' + ({w["phase"]:.10f}) - {w["omega"]:.10f} * Clock;',
                 ' float s, c; sincos(ph,s,c);',
                 f' h += {amp * 100 * geometry:.10f} * s;',
                 f' slope += float2({amp*kx:.10f},{amp*ky:.10f}) * c;', '}']
    code.append('return float3(h,slope) * WaveHeightScale;')
    (OUT / 'WaveField.hlsl').write_text('\n'.join(code) + '\n', encoding='utf-8')

    meta = json.loads((SOURCE / 'caustics/caustics.json').read_text(encoding='utf-8'))
    count, columns, tile, border = meta['frames'], 8, 512, 4
    rows = math.ceil(count / columns)
    atlas = Image.new('RGB', (columns * tile, rows * tile))
    interior = tile - 2 * border
    for i in range(count):
        with Image.open(SOURCE / f'caustics/caustics_{i:02d}.png') as frame:
            frame = frame.convert('RGB').resize((interior, interior), Image.Resampling.LANCZOS)
            # Wrapped gutters support fractional world tiling without adjacent-frame bleed.
            cell = Image.new('RGB', (tile, tile))
            for dx in (-interior, 0, interior):
                for dy in (-interior, 0, interior):
                    cell.paste(frame, (border + dx, border + dy))
            atlas.paste(cell, ((i % columns) * tile, (i // columns) * tile))
    atlas.save(OUT / 'T_ClearwaterCausticsAtlas.png')
    manifest = dict(source='https://github.com/Aureliengmz/clearwater',
                    license='MIT; Copyright (c) 2026 Lumaris',
                    wave_count=len(waves), wave_kernel='WaveField.hlsl',
                    atlas='T_ClearwaterCausticsAtlas.png', width=atlas.width, height=atlas.height,
                    columns=columns, rows=rows, tile=tile, border=border, frames=count,
                    loop_seconds=meta['loop_seconds'], patch_cm=meta['patch_m'] * 100,
                    baked_depth_cm=meta['depth_m'] * 100,
                    note='Interpolated baked caustics; no live FFT or live light focusing.',
                    tests_run=False)
    (OUT / 'production.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('CLEARWATER_NATIVE_DATA ' + json.dumps(manifest))


if __name__ == '__main__':
    main()
