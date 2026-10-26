"""Extract the pistol + knife dual-wield idle frames of BV1hQnh6hEio (file seconds, 30 fps).

Frames: Saved/Reference/DualPistolKukriBV1hQnh6hEio20261025/idle_frames/fNNNNN.png (frame index = file s * 30)
Sheets: .../sheets/idle_<name>.jpg
Usage: python -I extract_idle.py T0 T1 STEP NAME [COLS] [W]
"""
import cv2, numpy as np, os, sys

D = r"D:\FPS3D\FPSGAME\Saved\Reference\DualPistolKukriBV1hQnh6hEio20261025"
OUT = os.path.join(D, "idle_frames")


def frame(i, c):
    p = os.path.join(OUT, "f%05d.png" % i)
    if not os.path.exists(p):
        c.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, f = c.read()
        if not ok:
            return None
        cv2.imwrite(p, f)
    return cv2.imread(p)


def main():
    t0, t1, step, name = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    cols = int(sys.argv[5]) if len(sys.argv) > 5 else 4
    w = int(sys.argv[6]) if len(sys.argv) > 6 else 480
    os.makedirs(OUT, exist_ok=True)
    c = cv2.VideoCapture(os.path.join(D, "pistol_1280.mp4"))
    ims = []
    for i in range(int(round(t0 * 30)), int(round(t1 * 30)), step):
        f = frame(i, c)
        if f is None:
            break
        im = cv2.resize(f, (w, w // 2))
        cv2.putText(im, "%d %.2f" % (i, i / 30), (6, 22), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 255), 2)
        ims.append(im)
    while len(ims) % cols:
        ims.append(np.zeros_like(ims[0]))
    g = np.vstack([np.hstack(ims[k:k + cols]) for k in range(0, len(ims), cols)])
    cv2.imwrite(os.path.join(D, "sheets", "idle_%s.jpg" % name), g, [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == "__main__":
    main()
