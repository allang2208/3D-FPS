import sys, json, numpy as np
sys.path.insert(0, r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics')
import diag_lib as D
idle = json.loads((D.L201 / 'ClothFeed33/Inputs/201_idle.json').read_text())
loc = {n: D.mat(v) for n, v in zip(D.NAMES, idle['poses'][0])}
tr = {n: np.array([v]) for n, v in zip(D.NAMES, idle['poses'][0])}
W = D.worlds(tr)[0]
b = D.Body()
def part_idle(name):
    s = b.parts[name]
    sk = D.Skin(b.pos[s], (b.bi[s], b.bw[s]))
    return sk.pose(W)
np.set_printoptions(precision=2, suppress=True)
wr = W[D.BI['WPN_root']]
R = D.rot_only(wr[None])[0]
print('WPN_root idle axes (cols = local x,y,z in component):\n', R)
for n in ['LMG201_Cover', 'LMG201_Box', 'New_LMG201_Belt_00', 'New_LMG201_Belt_05']:
    p = part_idle(n)
    print(n, 'idle bbox', p.min(0), p.max(0), 'centroid', p.mean(0))
for k in range(6):
    p = part_idle('New_LMG201_Belt_%02d' % k)
    print('belt', k, 'centroid', p.mean(0), 'z', p[:, 2].min(), p[:, 2].max())
cv = part_idle('LMG201_Cover')
print('cover bone idle', W[D.BI['LMG201_Cover']][:3, 3])
# cover rear edge: vertices with max y (toward camera)
rear = cv[cv[:, 1] > cv[:, 1].max() - .6]
print('cover rear edge band', rear.min(0), rear.max(0))
top = cv[cv[:, 2] > cv[:, 2].max() - .4]
print('cover top band', top.min(0), top.max(0))
g = part_idle('WPN_root')
m = (g[:, 1] > -39) & (g[:, 1] < -23) & (g[:, 0] > -1) & (g[:, 0] < 12)
sub = g[m]
print('receiver under cover region z range', sub[:, 2].min(), sub[:, 2].max())
for y in (-36, -33, -30, -27, -25):
    s = g[(np.abs(g[:, 1] - y) < .6)]
    s = s[(s[:, 2] > -12)]
    print('section y', y, 'x', s[:, 0].min(), s[:, 0].max(), 'z', s[:, 2].min(), s[:, 2].max())
hg = g[(g[:, 1] < -38) & (g[:, 1] > -60)]
print('handguard idle bbox', hg.min(0), hg.max(0))
for n in ['hand_l', 'middle_01_l', 'index_01_l', 'pinky_01_l', 'thumb_01_l', 'lowerarm_l', 'upperarm_l', 'clavicle_l', 'hand_r', 'upperarm_r', 'lowerarm_r']:
    print(n, W[D.BI[n]][:3, 3])
h = W[D.BI['hand_l']]
f = D.unit(W[D.BI['middle_01_l']][:3, 3] - h[:3, 3])
a = D.unit(W[D.BI['index_01_l']][:3, 3] - W[D.BI['pinky_01_l']][:3, 3])
print('idle left finger dir', f, 'across(index-pinky)', a, 'palmar=cross(a,f)', D.unit(np.cross(a, f)))
print('eye action', D.camera(1)[0], 'eye hip', D.camera(0)[0])
