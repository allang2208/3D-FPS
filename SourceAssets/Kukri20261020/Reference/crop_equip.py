"""Zoomed NDC crops (x -0.1..0.8) of the 抛刀 reference for reading the knife spin and the catching hand."""
import cv2, numpy as np, os, sys
d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
CLIP_START = 1564
W, H = 1280, 720


def crop(i, x0=-0.1, x1=0.8, w=400):
    im = cv2.imread(os.path.join(d, "equip_frames", "f%05d.png" % i))
    for k in range(-8, 9):
        x = int((k / 8 * .5 + .5) * W); y = int((k / 8 * .5 + .5) * H)
        col = (0, 255, 255) if k == 0 else ((230, 230, 230) if k % 2 == 0 else (110, 110, 110))
        cv2.line(im, (x, 0), (x, H), col, 1); cv2.line(im, (0, y), (W, y), col, 1)
        if k % 2 == 0:
            cv2.putText(im, "%.2f" % (k / 8), (x + 2, H - 8), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 0), 2)
            cv2.putText(im, "%.2f" % (k / 8), (int((x0 * .5 + .5) * W) + 2, y - 3), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 0), 2)
    a, b = int((x0 * .5 + .5) * W), int((x1 * .5 + .5) * W)
    c = im[:, a:b]
    c = cv2.resize(c, (w, int(w * H / (b - a))))
    cv2.putText(c, "t=%.3f" % ((i - CLIP_START) / 30), (8, 40), cv2.FONT_HERSHEY_SIMPLEX, .9, (0, 0, 255), 2)
    return c


def sheet(idx, name, cols=5, **kw):
    ims = [crop(i, **kw) for i in idx]
    while len(ims) % cols:
        ims.append(np.zeros_like(ims[0]))
    cv2.imwrite(os.path.join(d, "sheets", name), np.vstack([np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)]),
                [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == "__main__":
    sheet(range(1568, 1578), "equip_crop_a.jpg")
    sheet(range(1578, 1588), "equip_crop_b.jpg", x0=-0.6, x1=0.8)
