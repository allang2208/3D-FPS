"""Tile reference frames into small contact sheets for reading (keep them under ~0.5 MB)."""
import argparse
from pathlib import Path

import cv2
import numpy as np

P = Path(__file__).parent


def build(start, end, step, cols, tile_w, out_name, label_every):
    # Frames are a contiguous 30 fps sequence; pick every round(step*fps)-th frame so the
    # selection never depends on float alignment with the requested start time.
    every = max(1, int(round(step / (1.0 / 30.0))))
    inside = []
    for path in sorted(P.joinpath('frames').glob('*.png')):
        seconds = float(path.name.split('_t')[1][:8])
        if start - 1e-4 <= seconds <= end + 1e-4:
            inside.append((seconds, path))
    picked = inside[::every]
    if not picked:
        raise SystemExit('no frames matched')

    sample = cv2.imread(str(picked[0][1]))
    tile_h = int(round(tile_w * sample.shape[0] / sample.shape[1]))
    rows = (len(picked) + cols - 1) // cols
    label_h = 16
    sheet = np.full((rows * (tile_h + label_h), cols * tile_w, 3), 24, np.uint8)
    for slot, (seconds, path) in enumerate(picked):
        image = cv2.imread(str(path))
        image = cv2.resize(image, (tile_w, tile_h), interpolation=cv2.INTER_AREA)
        r, c = divmod(slot, cols)
        y = r * (tile_h + label_h)
        sheet[y:y + tile_h, c * tile_w:(c + 1) * tile_w] = image
        text = '%.2f s' % seconds if slot % label_every == 0 else ''
        if text:
            cv2.putText(sheet, text, (c * tile_w + 4, y + tile_h + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (240, 240, 240), 1, cv2.LINE_AA)
    out = P / out_name
    cv2.imwrite(str(out), sheet, [cv2.IMWRITE_JPEG_QUALITY, 82])
    print('%s  %d frames  %dx%d  %.0f KB' % (out.name, len(picked), sheet.shape[1], sheet.shape[0], out.stat().st_size / 1024))
    print('  sampled: %s' % ', '.join('%.2f' % s for s, _ in picked))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('start', type=float)
    parser.add_argument('end', type=float)
    parser.add_argument('--step', type=float, default=0.1)
    parser.add_argument('--cols', type=int, default=6)
    parser.add_argument('--tile', type=int, default=210)
    parser.add_argument('--out', default='sheet.jpg')
    parser.add_argument('--label-every', type=int, default=1)
    args = parser.parse_args()
    build(args.start, args.end, args.step, args.cols, args.tile, args.out, args.label_every)
