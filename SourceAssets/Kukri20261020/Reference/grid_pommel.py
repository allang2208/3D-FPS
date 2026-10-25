"""NDC-grid reading sheets for the sprint-attack reference (melee #3 刀把 pommel strike, t = 0 at 89.733 s, frame 2692)."""
import cv2, numpy as np, os
d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
CLIP_START = 2692


def grid(im):
    h, w = im.shape[:2]
    for k in range(-8, 9):
        x = int((k / 8 * .5 + .5) * w); y = int((k / 8 * .5 + .5) * h)
        col = (0, 255, 255) if k == 0 else ((220, 220, 220) if k % 2 == 0 else (110, 110, 110))
        cv2.line(im, (x, 0), (x, h), col, 1); cv2.line(im, (0, y), (w, y), col, 1)
        if k % 2 == 0:
            cv2.putText(im, "%.2f" % (k / 8), (x + 2, h - 6), cv2.FONT_HERSHEY_SIMPLEX, .42, (0, 255, 0), 1)
            cv2.putText(im, "%.2f" % (k / 8), (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, .42, (0, 255, 0), 1)
    return im


def sheet(idx, name, cols=3, w=640):
    ims = []
    for i in idx:
        im = cv2.imread(os.path.join(d, "pommel_frames", "f%05d.png" % i)); im = grid(cv2.resize(im, (w, w * 9 // 16)))
        cv2.putText(im, "%d t=%.3f" % (i, (i - CLIP_START) / 30), (230, 22), cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 0, 255), 2)
        ims.append(im)
    while len(ims) % cols:
        ims.append(np.zeros_like(ims[0]))
    cv2.imwrite(os.path.join(d, "sheets", name), np.vstack([np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)]),
                [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == "__main__":
    sheet(range(2692, 2701), "pommel_grid_a.jpg")
    sheet(range(2701, 2710), "pommel_grid_b.jpg")
    sheet(range(2710, 2728, 2), "pommel_grid_c.jpg")
