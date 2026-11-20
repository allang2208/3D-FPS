"""Pack registered Quixel height, fine relief and cavity for the quarry stone materials."""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


PROJECT = Path(__file__).resolve().parents[3]
CACHE = PROJECT.parent / 'VaultCache' / 'FabLibrary'
OUTPUT = PROJECT / 'SourceAssets' / 'HillsQuarryCutYard' / 'StoneRelief'
SIZE = (2048, 2048)  # Existing quarry normal and albedo imports are capped at 2K.

# Each group uses its own scan's neutral height. Widths are expressed in the
# original 8-bit height units, so a broad elevation range on a small loose rock
# does not require clipping half of its atlas to black or white.
SCANS = (
    ('CliffA', 'Quarry_Cliff-5c019f10', 198., 17., 26.),
    ('CliffB', 'Quarry_Cliff-9caa4be4', 198., 22., 21.),
    ('Spoil', 'Small_Limestone_Rocks_Pack-09676e2a', 146., 53., 13.),
)


def source_map(folder, kind):
    source, = folder.glob(f'*_{kind}.jpg')
    with Image.open(source) as image:
        # These source maps are scalar data. Average each 2x2 footprint in
        # linear float space before quantizing the final packed texture once.
        linear = image.convert('L').convert('F').resize(SIZE, Image.Resampling.BOX)
    return np.asarray(linear)


def centered_channel(value, width):
    signed = value / width
    # Smooth shoulders keep the rare deep fractures and high fresh breaks distinct.
    normalized = .5 + .5 * signed / np.sqrt(1. + signed * signed)
    return np.rint(255. * normalized).astype(np.uint8)


def pack(name, cache_folder, level, depth_width, grain_width):
    folder = CACHE / cache_folder / 'Extracted'
    height = source_map(folder, 'Displacement')
    grain_source = height if name == 'Spoil' else source_map(folder, 'Bump')
    # Remove broad shape already present in R. This band retains real local
    # pits and grain on the small rocks, for which Quixel supplies no bump map.
    grain = grain_source - gaussian_filter(grain_source, sigma=2.2, mode='nearest')
    cavity = source_map(folder, 'Cavity')
    channels = np.stack((centered_channel(height - level, depth_width),
                         centered_channel(grain, grain_width),
                         np.rint(cavity).astype(np.uint8)), axis=-1)
    path = OUTPUT / f'T_Quarry{name}Relief.png'
    Image.fromarray(channels).save(path)
    quantiles = np.percentile(channels[::4, ::4], [5, 50, 95], axis=(0, 1))
    print(f'{path.name}  RGB P5, P50, P95 = {quantiles.astype(int).tolist()}')


if __name__ == '__main__':
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for scan in SCANS:
        pack(*scan)
