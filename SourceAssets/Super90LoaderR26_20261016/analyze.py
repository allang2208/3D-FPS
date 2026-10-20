"""Author inputs: grip axes on the pusher and flick turnaround directions."""
import sys
import numpy as np
from scipy.spatial.transform import Rotation as R
from r26_core import *

role = sys.argv[1] if len(sys.argv) > 1 else 'normal_7'
W = [world(row) for row in posed_local(role)]
g = lambda f, n: np.linalg.inv(W[f][GUN]) @ W[f][n]
f = 100
post, hand = g(f, POST), g(f, 'hand_l')
c = post[:3, 3]
width = norm(g(f, 'index_01_l')[:3, 3] - g(f, 'pinky_01_l')[:3, 3])
fingers = norm(g(f, 'middle_01_l')[:3, 3] - hand[:3, 3])
fore = norm(hand[:3, 3] - g(f, 'lowerarm_l')[:3, 3])
palm = norm(np.cross(fingers, width))
push = norm(g(110, POST)[:3, 3] - g(90, POST)[:3, 3])
print('pivot(post) to wrist mm', np.round((c - hand[:3, 3]) * 1000, 1), np.linalg.norm(c - hand[:3, 3]) * 1000)
print('palm normal . (post - wrist)', np.dot(palm, norm(c - hand[:3, 3])))
for i, a in enumerate('XYZ'):
    ax = post[:3, i]
    print('post axis', a, 'dot width %.3f fingers %.3f fore %.3f palm %.3f push %.3f' % tuple(np.dot(ax, v) for v in (width, fingers, fore, palm, push)))
print('push . width %.3f fingers %.3f fore %.3f palm %.3f' % tuple(np.dot(push, v) for v in (width, fingers, fore, palm)))
tips = {d: g(f, d + ('_03_l' if d != 'thumb' else '_03_l'))[:3, 3] for d in DIGITS}
for d, p in tips.items():
    print('tip', d, 'to pivot mm %.1f' % (np.linalg.norm(p - c) * 1000))
# Rotation sign: +theta about width moves the middle tip along push?
tip = tips['middle'] - c
print('d(tip)/d(theta about width) . push', np.dot(np.cross(width, tip), push))
# flick turnaround
P = np.array([g(i, 'hand_l')[:3, 3] for i in range(len(W))])
V = np.gradient(P, axis=0) * FPS
for a, b in ((114, 118), (124, 128), (116, 119), (123, 126)):
    print('dir %d-%d' % (a, b), np.round(norm(P[b] - P[a]), 3), 'speed', np.round(np.linalg.norm(V[a:b + 1], axis=1), 2))
print('angle out/back deg', np.degrees(np.arccos(np.clip(np.dot(norm(P[119] - P[114]), norm(P[127] - P[123])), -1, 1))))
print('extreme', np.round(P[121] * 1000, 1), 'tube drop pos at 112/118', np.round(g(112, TUBE)[:3, 3] * 1000, 1), np.round(g(118, TUBE)[:3, 3] * 1000, 1))
print('gun up(local Z) etc: hand pos at 100', np.round(hand[:3, 3] * 1000, 1), 'at 121', np.round(P[121] * 1000, 1), 'at 144', np.round(P[-1] * 1000, 1))
# finger flexion axes from grasp (100) to splay (116)
for n in FINGERS:
    q0 = R.from_quat(posed_local(role)[100][n][3:7]) if False else None
rows = posed_local(role)
for n in FINGERS:
    a, b = R.from_quat(rows[100][n][3:7]), R.from_quat(rows[116][n][3:7])
    rel = a * b.inv()
    rv = rel.as_rotvec()
    print('%-22s open->grasp %6.1f deg axis(parent) %s' % (n, np.degrees(np.linalg.norm(rv)), np.round(norm(rv), 3)))
