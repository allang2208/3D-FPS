"""Extract the quick-melee (pommel strike) reference frames (BV1CeYUeSE7b 1:29.0-1:33.0, around the pommel strike used for the kukri quick melee) and an overview sheet.

Frames: Saved/Reference/KukriBV1CeYUeSE7b20261020/pommel_frames/fNNNNN.png (frame index at 30 fps).
Sheets: Saved/Reference/KukriBV1CeYUeSE7b20261020/sheets/pommel_*.jpg
"""
import cv2, numpy as np, os, sys

D = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
OUT = os.path.join(D, "pommel_frames")
T0, T1 = 89.0, 93.0


def extract():
    os.makedirs(OUT, exist_ok=True)
    c = cv2.VideoCapture(os.path.join(D, "ref.f100024.mp4"))
    fps = c.get(cv2.CAP_PROP_FPS)
    a, b = int(round(T0 * fps)), int(round(T1 * fps))
    c.set(cv2.CAP_PROP_POS_FRAMES, a)
    for i in range(a, b):
        ok, f = c.read()
        if not ok:
            break
        cv2.imwrite(os.path.join(OUT, "f%05d.png" % i), f)
    print("fps", fps, "frames", a, b)


def sheets(a, b, step, name, cols=6, w=320):
    ims = []
    for i in range(a, b, step):
        p = os.path.join(OUT, "f%05d.png" % i)
        if not os.path.exists(p):
            continue
        im = cv2.resize(cv2.imread(p), (w, w * 9 // 16))
        cv2.putText(im, "%d %.3f" % (i, i / 30), (6, 22), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 255), 2)
        ims.append(im)
    while len(ims) % cols:
        ims.append(np.zeros_like(ims[0]))
    os.makedirs(os.path.join(D, "sheets"), exist_ok=True)
    cv2.imwrite(os.path.join(D, "sheets", name), np.vstack([np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)]),
                [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == "__main__":
    if "--sheets" not in sys.argv:
        extract()
    sheets(2670, 2790, 3, "pommel_overview.jpg", cols=8, w=280)
