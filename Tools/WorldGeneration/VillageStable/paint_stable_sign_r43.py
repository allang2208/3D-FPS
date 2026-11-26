"""Rasterize Stable.svg onto the two independent weathered R2 oak trade-sign faces."""
from pathlib import Path
import sys
from xml.etree import ElementTree

import numpy as np
from PIL import Image
from fontTools.svgLib.path import parse_path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path[:0] = [
    str(HERE.parent / 'VillageTradeSigns'),
    str(HERE.parent / 'VillageBlacksmith/ForgeR2'),
]
from paint import PaintedPath
from weather_wood import grain, n

SOURCE = PROJECT / 'SourceAssets/HillsVillageTradeSigns'


def main():
    design = SOURCE / 'Stable.svg'
    canvas = Image.new('RGB', (2 * n, 2 * n))
    for path in ElementTree.parse(design).getroot():
        parse_path(path.attrib['d'], PaintedPath(canvas, path))
    paint = np.asarray(canvas.resize((n, n), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
    faces = [grain(side, paint)[0] for side in (0, 1)]
    out_arr = np.concatenate(faces, axis=1)
    mean_rgb = out_arr.mean(axis=(0, 1)) / 255.0
    assert float(mean_rgb.min()) > 0.08, f'Unexpected dark sign output: {mean_rgb}'
    out_path = SOURCE / 'T_StableSign_Color.png'
    Image.fromarray(out_arr).save(out_path)
    print(f'STABLE_SIGN_PAINTED {out_path} size={out_arr.shape[1]}x{out_arr.shape[0]} mean_rgb={mean_rgb.round(3).tolist()}')


if __name__ == '__main__':
    main()
