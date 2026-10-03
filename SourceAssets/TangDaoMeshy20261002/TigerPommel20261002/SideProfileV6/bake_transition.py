"""Bake front-edge and side-mane PBR into the continuous shell's own UV domain."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from profile_surface import side_projection

P = Path(__file__).resolve().parent
BASE = P.parent
params = json.loads((P / 'transition_surface.json').read_text(encoding='utf-8'))
order = np.argsort(params['u'])
edge_u = np.asarray(params['u'])[order]
edge_fu = np.asarray(params['face_u'])[order]
edge_fv = np.asarray(params['face_v'])[order]
periodic_u = np.r_[edge_u - 1, edge_u, edge_u + 1]
n = 2048
uu = np.linspace(0, 1, n, dtype=np.float32)[None, :]
fu = np.interp(uu, periodic_u, np.tile(edge_fu, 3))
fv = np.interp(uu, periodic_u, np.tile(edge_fv, 3))

def sample(data, u, v):
    x, y = np.broadcast_arrays(np.clip(u, 0, 1) * (data.shape[1] - 1),
                                np.clip(v, 0, 1) * (data.shape[0] - 1))
    ix, iy = x.astype(np.int32), y.astype(np.int32)
    jx, jy = np.minimum(ix + 1, data.shape[1] - 1), np.minimum(iy + 1, data.shape[0] - 1)
    fx, fy = (x - ix)[..., None], (y - iy)[..., None]
    return ((data[iy, ix] * (1 - fx) + data[iy, jx] * fx) * (1 - fy)
            + (data[jy, ix] * (1 - fx) + data[jy, jx] * fx) * fy)

def smooth(a, b, value):
    q = np.clip((value - a) / (b - a), 0, 1)
    return q * q * (3 - 2 * q)

def decode(value):
    return np.where(value <= .04045, value / 12.92, ((value + .055) / 1.055) ** 2.4)

def encode(value):
    return np.where(value <= .0031308, value * 12.92, 1.055 * np.maximum(value, 0) ** (1 / 2.4) - .055)

for key in ('BaseColor', 'ORM', 'Normal'):
    filename = 'TangDao_TigerPommel_ChasedBody_' + key + '.png'
    front = np.asarray(Image.open(BASE / 'Textures' / ('TangDao_TigerPommel_BronzeFace_' + key + '.png')).convert('RGB'), np.float32) / 255
    body = np.asarray(Image.open(P / 'TexturesRaw' / filename).convert('RGB'), np.float32) / 255
    front_n=4096
    front_result=np.empty((front_n,front_n,3),np.uint8)
    front_u=np.linspace(0,1,front_n,dtype=np.float32)[None,:]
    for row in range(0,front_n,128):
        end=min(row+128,front_n)
        front_v=np.arange(row,end,dtype=np.float32)[:,None]/(front_n-1)
        side_u,side_v,weight=side_projection((front_u-.5)*.082,(.5-front_v)*.09)
        side=sample(body,side_u,side_v)
        original=front[row:end]
        weight=weight[...,None]
        if key=='BaseColor':
            pixels=encode(decode(original)*(1-weight)+decode(side)*weight)
        elif key=='Normal':
            # This front grid has a different tangent frame; retain only its
            # original front micro-detail. Side mane shape is in the mesh.
            normal=original*2-1
            normal[...,:2]*=1-weight
            normal/=np.maximum(np.linalg.norm(normal,axis=2,keepdims=True),1e-8)
            pixels=normal*.5+.5
        else:
            pixels=original*(1-weight)+side*weight
        front_result[row:end]=np.clip(pixels*255+.5,0,255).astype(np.uint8)
    Image.fromarray(front_result).save(P/'Textures'/('TangDao_TigerPommel_BronzeFace_'+key+'.png'))
    front=front_result.astype(np.float32)/255
    result = np.empty((n, n, 3), np.uint8)
    for row in range(0, n, 128):
        end = min(row + 128, n)
        t = np.arange(row, end, dtype=np.float32)[:, None] / (n - 1)
        blend = smooth(0, min(.065, params['join']), t)[..., None]
        beta = params['beta_start'] + (np.pi / 2 - params['beta_start']) * t
        body_v = (beta + np.pi / 2) / np.pi
        # Preserve the contour texel exactly; carry the shallow chased pattern
        # inward slightly while the side pattern takes over across the patch.
        inward = .03 * smooth(0, min(.065, params['join']), t)
        face = sample(front, .5 + (fu - .5) * (1 - inward), .5 + (fv - .5) * (1 - inward))
        side = sample(body, uu, body_v)
        if key == 'BaseColor':
            pixels = encode(decode(face) * (1 - blend) + decode(side) * blend)
        elif key == 'Normal':
            # The geometric relief supplies the primary edge shape. Fade the
            # micro-normal into the shell's different tangent frame smoothly.
            normal = side * 2 - 1
            normal[..., :2] *= blend
            normal[..., 2] = normal[..., 2] * blend[..., 0] + 1 - blend[..., 0]
            normal /= np.maximum(np.linalg.norm(normal, axis=2, keepdims=True), 1e-8)
            pixels = normal * .5 + .5
        else:
            pixels = face * (1 - blend) + side * blend
        result[row:end] = np.clip(pixels * 255 + .5, 0, 255).astype(np.uint8)
    Image.fromarray(result).save(P / 'Textures' / filename)

(P / 'transition_bake.json').write_text(json.dumps({
    'resolution': n, 'uv_domain': 'circumference u / front-to-back shell t',
    'color': 'linear-light front-edge to side-mane interpolation',
    'orm': 'same boundary correspondence as geometry',
    'normal': 'geometric edge relief with gradually introduced side micro-normal',
    'raw_texture_directory': 'TexturesRaw', 'join_parameter': params['join'],
    'front_atlas_resolution':4096,'cheek_geometry_and_color':'same spherical side-mane field; frontal features retained centrally',
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('TIGER_V6_CONTINUOUS_JUNCTION_PBR_BAKED', flush=True)
