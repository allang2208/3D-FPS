"""NDC reading grids for the dual idle hold frames (x right, y down, [-1,1] over the 1280x640 frame).

Output: Saved/Reference/DualPistolKukriBV1hQnh6hEio20261025/sheets/grid_<frame>.jpg
"""
import cv2, os, sys

D = r"D:\FPS3D\FPSGAME\Saved\Reference\DualPistolKukriBV1hQnh6hEio20261025"


def grid(i, alpha=1.7, beta=25):
    f = cv2.imread(os.path.join(D, "idle_frames", "f%05d.png" % i))
    f = cv2.convertScaleAbs(f, alpha=alpha, beta=beta)
    h, w = f.shape[:2]
    for k in range(-10, 11):
        x = int((k / 10 + 1) / 2 * w)
        y = int((k / 10 + 1) / 2 * h)
        col = (0, 200, 255) if k % 5 == 0 else (90, 90, 90)
        cv2.line(f, (x, 0), (x, h), col, 1)
        cv2.line(f, (0, y), (w, y), col, 1)
        cv2.putText(f, "%.1f" % (k / 10), (x + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, .35, (0, 255, 255), 1)
        cv2.putText(f, "%.1f" % (k / 10), (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, .35, (0, 255, 255), 1)
    cv2.imwrite(os.path.join(D, "sheets", "grid_%05d.jpg" % i), f, [cv2.IMWRITE_JPEG_QUALITY, 90])


if __name__ == "__main__":
    for a in sys.argv[1:]:
        grid(int(a))
