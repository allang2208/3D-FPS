"""Register static scenery to the first source frame and fit apparent UE view rotation."""
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'Reference'
HEADER = ROOT.parents[1] / 'Source/FPSGAME/Weapons/ChainSlashCameraKeys.inl'
START, END = 2238, 2400
W, H = 960, 540
FOCAL = .5 * H / np.tan(np.deg2rad(75. / 2))
detector = cv2.SIFT_create(nfeatures=2300)
matcher = cv2.BFMatcher()
cv2.setNumThreads(3)
cv2.setRNGSeed(9)

def features(index):
    frame = cv2.imread(str(REFERENCE / f'f{index:04}.jpg'), cv2.IMREAD_GRAYSCALE)
    frame = cv2.resize(frame, (W, H), interpolation=cv2.INTER_AREA)
    mask = np.full(frame.shape, 255, np.uint8)
    mask[:int(.174 * H), :int(.81 * W)] = 0   # fixed title overlay
    keys, desc = detector.detectAndCompute(frame, mask)
    return np.float64([k.pt for k in keys]), desc

def rays(uv):
    v = np.column_stack(((uv - [W / 2, H / 2]) / FOCAL, np.ones(len(uv))))
    return v / np.linalg.norm(v, axis=1, keepdims=True)

base, desc = features(START)
basis = np.array([[0,1,0], [0,0,-1], [1,0,0]], float)
keys = []
for i in range(START, END + 1):
    uv, descriptors = features(i)
    pairs = [a for a,b in matcher.knnMatch(desc, descriptors, k=2) if a.distance < .75 * b.distance]
    old = np.array([base[m.queryIdx] for m in pairs])
    new = np.array([uv[m.trainIdx] for m in pairs])
    _, inliers = cv2.findHomography(old, new, cv2.RANSAC, 2.5)
    if inliers is None or inliers.sum() < 16:
        raise RuntimeError(f'Scenery registration lost at frame {i}')
    ok = inliers.ravel().astype(bool)
    first, second = rays(old[ok]), rays(new[ok])
    # Equalize screen regions so a single highly textured moving foreground
    # cannot pull the pose toward one side.
    cells = (old[ok,0] // 120 + 8 * (old[ok,1] // 90)).astype(int)
    weights = 1 / np.bincount(cells)[cells]
    u, _, v = np.linalg.svd((second * weights[:,None]).T @ first)
    delta = u @ np.diag([1., 1., np.linalg.det(u @ v)]) @ v
    camera = basis.T @ delta.T @ basis
    pitch = np.arcsin(np.clip(camera[2,0], -1, 1))
    yaw = np.arctan2(camera[1,0], camera[0,0])
    roll = np.arctan2(-camera[2,1], camera[2,2])
    keys.append(np.rad2deg([pitch, yaw, roll]))
keys = np.array(keys)
# Remove the end-of-take resting offset only over the existing recovery.
t = np.arange(len(keys)) / 60
u = np.clip((t - 2.22) / (2.70 - 2.22), 0, 1)
keys -= u[:,None]**2 * (3 - 2*u[:,None]) * keys[-1].copy()
keys[[0,-1]] = 0
lines = ['// Fitted from source frames 2238-2400 at 60 Hz (pitch, yaw, roll in degrees).']
lines += ['    {%.5ff, %.5ff, %.5ff},' % tuple(k) for k in keys]
HEADER.write_text('\n'.join(lines)+'\n', encoding='utf-8')
print('Camera keys:',len(keys),'peak angles:',np.round(abs(keys).max(axis=0),2))
