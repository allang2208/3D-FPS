"""Write UE-space pose sets for render_preview.py and run Blender on them."""
import json
import math
import subprocess
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
BLENDER = r"E:\Program Files\Blender Foundation\Blender 5.1\blender.exe"


def edge_from_roll(b, deg):
    b = np.asarray(b, float); b = b / np.linalg.norm(b)
    a = np.cross(b, [0, 0, 1]); a = a / np.linalg.norm(a)
    c = np.cross(a, b)
    ph = math.radians(deg)
    return -c * math.cos(ph) + a * math.sin(ph)


def write_poses(poses, path):
    """poses: {name: (world dict of T, K T)}"""
    out = {'poses': {}}
    for name, (world, K) in poses.items():
        out['poses'][name] = {'bones': {n: t.pack() for n, t in world.items()}, 'kukri': K.pack()}
    Path(path).write_text(json.dumps(out), encoding='utf-8')


def render(poses_json, out_dir, width=640):
    cmd = [BLENDER, '-b', '--factory-startup', '--python', str(P / 'render_preview.py'), '--',
           str(Path(poses_json).resolve()), str(Path(out_dir).resolve()), str(width)]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    lines = [l for l in res.stdout.splitlines() if 'KUKRI_PREVIEW' in l or 'Error' in l or 'Traceback' in l]
    if res.returncode != 0:
        lines.append(res.stdout[-3000:])
        lines.append(res.stderr[-3000:])
    return lines


def sheet(out_dir, names, path, cols=3, label=True):
    import cv2
    imgs = []
    for n in names:
        im = cv2.imread(str(Path(out_dir) / (n + '.png')))
        if im is None:
            continue
        if label:
            cv2.putText(im, n, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 255), 2)
        h, w = im.shape[:2]
        for i in range(1, 4):
            cv2.line(im, (i * w // 4, 0), (i * w // 4, h), (90, 90, 90), 1)
            cv2.line(im, (0, i * h // 4), (w, i * h // 4), (90, 90, 90), 1)
        imgs.append(im)
    while len(imgs) % cols:
        imgs.append(np.zeros_like(imgs[0]))
    rows = [np.hstack(imgs[i:i + cols]) for i in range(0, len(imgs), cols)]
    cv2.imwrite(str(path), np.vstack(rows))

