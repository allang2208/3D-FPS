"""Transfer the old rim decoration into continuous UVs and author clean PBR."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter

P = Path(__file__).resolve().parent
SRC = P.parent / 'Meshy/candidate01/downloads'
SIZE = 2048
data = np.load(P / 'surface_transfer.npz')
uv, source, points = data['uv'], data['old_uv'], data['points']
source_maps = {key: np.asarray(Image.open(SRC / name).convert('RGB'), dtype=np.float32)/255.
               for key, name in [('base', 'texture_0.png'), ('rough', 'texture_0_roughness.png'),
                                 ('metal', 'texture_0_metallic.png'), ('normal', 'texture_0_normal.png')]}
source_maps['base'] = np.where(source_maps['base'] <= .04045, source_maps['base']/12.92,
                                ((source_maps['base']+.055)/1.055)**2.4)
y, x = np.mgrid[:SIZE, :SIZE].astype(np.float32)
rng = np.random.default_rng(20261002)
grain = gaussian_filter(rng.standard_normal((SIZE, SIZE)).astype(np.float32), .65)
grain /= max(float(grain.std()), 1.e-6)
# Submillimetre milling grain, without dark bands, dirt or baked illumination.
fine = .5*np.sin(x*.83+y*.037)+.3*np.sin(x*1.43-y*.027)+.2*np.sin(y*.43+x*.11)
height = .08*fine + .045*grain
dhdy, dhdx = np.gradient(height)
clean_normal = np.dstack((-dhdx*.35, dhdy*.35, np.ones_like(x)))
clean_normal /= np.linalg.norm(clean_normal, axis=2, keepdims=True)
field = np.clip(.13 + .0016*grain, .122, .138)
clean_base = np.dstack((field*.96, field, field*1.025))
base = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
normal = np.zeros_like(base)
orm = np.zeros_like(base)
filled = np.zeros((SIZE, SIZE), dtype=bool)

def sampled(image, coords):
    h, w = image.shape[:2]
    px = np.clip(coords[:, 0], 0., 1.)*(w-1)
    py = (1-np.clip(coords[:, 1], 0., 1.))*(h-1)
    ix, iy = px.astype(int), py.astype(int)
    jx, jy = np.minimum(ix+1, w-1), np.minimum(iy+1, h-1)
    a, b = (px-ix)[:, None], (py-iy)[:, None]
    return ((image[iy, ix]*(1-a)+image[iy, jx]*a)*(1-b) +
            (image[jy, ix]*(1-a)+image[jy, jx]*a)*b)

def frame(p, tex):
    a, b = p[1]-p[0], p[2]-p[0]
    ta, tb = tex[1]-tex[0], tex[2]-tex[0]
    det = ta[0]*tb[1]-ta[1]*tb[0]
    if abs(det) < 1.e-12:
        return np.eye(3)
    n = np.cross(a, b)
    n /= max(np.linalg.norm(n), 1.e-12)
    t = (a*tb[1]-b*ta[1])/det
    t -= n*np.dot(t, n)
    t /= max(np.linalg.norm(t), 1.e-12)
    raw_b = (-a*tb[0]+b*ta[0])/det
    bitangent = np.cross(n, t)
    if np.dot(bitangent, raw_b) < 0:
        bitangent *= -1
    return np.stack((t, bitangent, n), axis=1)

for index, triangle in enumerate(uv):
    a, b, c = triangle*SIZE
    lo = np.floor(np.minimum(np.minimum(a, b), c)).astype(int)
    hi = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
    lo[0], hi[0] = max(lo[0], 0), min(hi[0], SIZE-1)
    if hi[0] < lo[0] or hi[1] < lo[1]:
        continue
    gx, gy = np.meshgrid(np.arange(lo[0], hi[0]+1), np.arange(lo[1], hi[1]+1))
    q = np.column_stack((gx.ravel()+.5, gy.ravel()+.5))
    e1, e2 = b-a, c-a
    det = e1[0]*e2[1]-e1[1]*e2[0]
    if abs(det) < 1.e-9:
        continue
    delta = q-a
    w1 = (delta[:, 0]*e2[1]-delta[:, 1]*e2[0])/det
    w2 = (e1[0]*delta[:, 1]-e1[1]*delta[:, 0])/det
    w0 = 1-w1-w2
    inside = (w0 >= -1.e-5)&(w1 >= -1.e-5)&(w2 >= -1.e-5)
    if not np.any(inside):
        continue
    weights = np.column_stack((w0, w1, w2))[inside]
    xx = gx.ravel()[inside]
    yy = SIZE-1-(gy.ravel()[inside] % SIZE)
    old_coords = weights @ source[index]
    root_mix = np.clip(weights @ data['blend'][index], 0., 1.)[:, None]
    rim = np.clip(weights @ data['ornament'][index], 0., 1.)[:, None]
    old_base = sampled(source_maps['base'], old_coords)
    # Retain the authored engraving contrast and modest warm trim, limiting the
    # overbright painted highlight. The broad central field uses clean steel.
    rim_base = np.clip(old_base, .015, .42)*.72 + np.array([.045, .047, .05])
    new_base = clean_base[yy, xx]*(1-rim) + rim_base*rim
    base[yy, xx] = old_base*(1-root_mix)+new_base*root_mix
    old_rough = sampled(source_maps['rough'], old_coords)[:, :1]
    old_metal = sampled(source_maps['metal'], old_coords)[:, :1]
    new_rough = np.clip(.48+.007*grain[yy, xx, None]-.105*rim, .35, .51)
    orm[yy, xx, 0] = 1.
    orm[yy, xx, 1:2] = old_rough*(1-root_mix)+new_rough*root_mix
    orm[yy, xx, 2:3] = old_metal*(1-root_mix)+root_mix
    # Source OpenGL normals must be rotated into UV0's new tangent frame before
    # interpolation. Fine detail uses UV0 too; UE flips G on import exactly once.
    old_n = sampled(source_maps['normal'], old_coords)*2-1
    old_n /= np.maximum(np.linalg.norm(old_n, axis=1, keepdims=True), 1.e-8)
    conversion = frame(points[index], triangle).T @ frame(points[index], source[index])
    mapped_n = old_n @ conversion.T
    mapped_n[:, 2] = np.maximum(mapped_n[:, 2], .15)
    mapped_n /= np.maximum(np.linalg.norm(mapped_n, axis=1, keepdims=True), 1.e-8)
    detail = (1-root_mix)+root_mix*rim*.32
    n = clean_normal[yy, xx]*(1-detail)+mapped_n*detail
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1.e-8)
    normal[yy, xx] = n*.5+.5
    filled[yy, xx] = True

# Nearest-texel dilation avoids dark mip fringes at the two horn islands. The
# cylindrical seam wraps while rasterising and both sides retain their pattern.
nearest = distance_transform_edt(~filled, return_distances=False, return_indices=True)
for target in (base, normal, orm):
    target[~filled] = target[nearest[0][~filled], nearest[1][~filled]]
base = np.where(base <= .0031308, base*12.92, 1.055*np.maximum(base, 0.)**(1/2.4)-.055)
for key, pixels in [('BaseColor', base), ('Normal', normal), ('ORM', orm)]:
    Image.fromarray(np.uint8(np.clip(pixels, 0., 1.)*255+.5), 'RGB').save(P / 'Textures' / ('T_ClovenWing_'+key+'.png'))
(P / 'texture_recipe.json').write_text(json.dumps({'size': SIZE, 'color_space': 'BaseColor sRGB; Normal/ORM linear',
    'normal_convention': 'OpenGL; UE import flip_green_channel=True', 'metallic': 1.,
    'body_roughness': .48, 'rim_roughness': .375, 'body_base_linear': [.1248, .13, .13325],
    'seed': 20261002, 'retained': 'Existing rim engraving and feathered original root finish',
    'tested': False}, indent=2), encoding='utf-8')
print('CLOVEN_TEXTURES_AUTHORED 3 x 2048', flush=True)
