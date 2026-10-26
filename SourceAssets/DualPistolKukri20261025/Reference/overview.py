"""Overview contact sheets of the BV1hQnh6hEio pistol chapter, to locate the pistol + blade dual wield.

Input:  Saved/Reference/DualPistolKukriBV1hQnh6hEio20261025/pistol_1280.mp4 (file time 0 = video 0:00)
Output: .../sheets/ov_<start>.jpg, one tile every STEP seconds, labelled with file seconds.
"""
import cv2, numpy as np, os, sys

D = r"D:\FPS3D\FPSGAME\Saved\Reference\DualPistolKukriBV1hQnh6hEio20261025"
STEP = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
T0 = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
T1 = float(sys.argv[3]) if len(sys.argv) > 3 else 360.0
COLS, ROWS, W = 6, 5, 320


def main():
    c = cv2.VideoCapture(os.path.join(D, "pistol_1280.mp4"))
    os.makedirs(os.path.join(D, "sheets"), exist_ok=True)
    tiles, t, start = [], T0, T0
    while t < T1:
        c.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = c.read()
        if not ok:
            break
        im = cv2.resize(f, (W, W // 2))
        cv2.putText(im, "%.1f" % t, (4, 18), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 255, 255), 2)
        tiles.append(im)
        t += STEP
        if len(tiles) == COLS * ROWS:
            flush(tiles, start)
            tiles, start = [], t
    if tiles:
        flush(tiles, start)


def flush(tiles, start):
    while len(tiles) % COLS:
        tiles.append(np.zeros_like(tiles[0]))
    g = np.vstack([np.hstack(tiles[i:i + COLS]) for i in range(0, len(tiles), COLS)])
    cv2.imwrite(os.path.join(D, "sheets", "ov_%05.1f.jpg" % start), g, [cv2.IMWRITE_JPEG_QUALITY, 80])


if __name__ == "__main__":
    main()
