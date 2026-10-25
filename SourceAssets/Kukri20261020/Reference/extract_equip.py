"""Extract the 切刀 reference frames (BV1CeYUeSE7b 52.0-55.5 s, toss-and-catch draw) and build contact sheets.

Frames: Saved/Reference/KukriBV1CeYUeSE7b20261020/equip_frames/fNNNNN.png (frame index at 30 fps).
Sheets: Saved/Reference/KukriBV1CeYUeSE7b20261020/sheets/equip_*.jpg
"""
import cv2, numpy as np, os, glob, sys

D = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
OUT = os.path.join(D, "equip_frames")
T0, T1 = 52.0, 55.5


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


def sheet(sel, name, cols=4, w=480):
    ims = []
    for f in sel:
        im = cv2.imread(f)
        i = int(os.path.basename(f)[1:6])
        im = cv2.resize(im, (w, w * 9 // 16))
        cv2.putText(im, "%d %.3f" % (i, i / 30), (6, 22), cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 255, 255), 2)
        ims.append(im)
    while len(ims) % cols:
        ims.append(np.zeros_like(ims[0]))
    os.makedirs(os.path.join(D, "sheets"), exist_ok=True)
    cv2.imwrite(os.path.join(D, "sheets", name),
                np.vstack([np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)]), [cv2.IMWRITE_JPEG_QUALITY, 85])


def sheets(a, b, step, name, cols=4, w=480):
    files = [os.path.join(OUT, "f%05d.png" % i) for i in range(a, b, step)]
    sheet([f for f in files if os.path.exists(f)], name, cols, w)


if __name__ == "__main__":
    if "--sheets" not in sys.argv:
        extract()
    # overview: every 3rd frame
    sheets(1560, 1665, 3, "equip_overview.jpg", cols=6, w=320)
