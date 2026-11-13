"""Author original packed steel fields and blade-space profiles; no preview render."""
import json
import runpy
from pathlib import Path
import bpy
import numpy as np

P = Path(__file__).resolve().parent
TEXTURES = P / 'Textures'
TEXTURES.mkdir(exist_ok=True)
NX, NY = 2048, 4096
WX, WZ = 12., 88.
runpy.run_path(str(P/'ReferenceRefinementV3/patterns.py'))['author'](TEXTURES)

old = json.loads((P.parent / 'DaoLongitudinal20261110/layouts.json').read_text(encoding='utf-8'))
families = {'factory': 'Flow', 'extended_edge': 'Flow', 'chixiao': 'Flow', 'zhufeng': 'Flow',
            'heavy_spine': 'Twist', 'tengyun_dragon': 'Twist',
            'feather_edge': 'Feather', 'yanling_edge': 'Feather'}
profiles = {}
for choice, family in families.items():
    source = old['zhanmadao/' + choice]['source']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=source)
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    objects = [o for o in objects if 'LOD0' in o.name] or objects
    triangles = []
    for obj in objects:
        mesh = obj.data; mesh.calc_loop_triangles()
        points = np.asarray([tuple(v.co) for v in mesh.vertices])*100
        triangles.append(points[np.asarray([tuple(t.vertices) for t in mesh.loop_triangles])])
    tri = np.concatenate(triangles)
    low, high = float(tri[:, :, 2].min()), float(tri[:, :, 2].max())
    stations = np.linspace(low+.005*(high-low), high-.002*(high-low), 33)
    centers, widths = [], []
    for station in stations:
        cuts = []
        for a, b in [(0, 1), (1, 2), (2, 0)]:
            pa, pb = tri[:, a], tri[:, b]; dz = pb[:, 2]-pa[:, 2]
            valid = (np.abs(dz)>1e-8) & ((pa[:, 2]-station)*(pb[:, 2]-station)<=0)
            t = (station-pa[valid, 2])/dz[valid]
            cuts.append(pa[valid]+(pb[valid]-pa[valid])*t[:, None])
        section = np.concatenate(cuts)
        left, right = float(section[:, 0].min()), float(section[:, 0].max())
        centers.append((left+right)*.5); widths.append(max(right-left, .02))
    arc = np.r_[0., np.cumsum(np.hypot(np.diff(stations), np.diff(centers)))]
    profiles[choice] = dict(family=family, source=source, z=stations.tolist(),
                            center=centers, width=widths, arc=arc.tolist(), blade_z=[low, high])
(P/'profiles.json').write_text(json.dumps(profiles, indent=2)+'\n', encoding='utf-8')
(P/'author-receipt.json').write_text(json.dumps(dict(patterns=list(families.values()),
    blades=list(families), resolution=[NX, NY], field_size_cm=[WX, WZ],
    channels=['alloy layers', 'signed etch slope X', 'signed etch slope Z', 'polish variation'],
    origin='original procedural contour fields', art_revision='ReferenceV3', geometry_changed=False, rendered=False), indent=2)+'\n', encoding='utf-8')
print('DAMASCUS_FIELDS_AUTHORED 3 PROFILES 8')
