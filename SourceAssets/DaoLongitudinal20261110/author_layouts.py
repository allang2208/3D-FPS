"""Fit private longitudinal lanes to the fourteen exported TangDao/Zhanmadao blades."""
import json
from pathlib import Path
import bpy
import numpy as np

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
S = ROOT / 'SourceAssets'
Z = S / 'Zhanmadao20261018'
sources = {'zhanmadao/factory': Z / 'Export/SM_Zhanmadao_Blade_V1.fbx'}
sources.update({'zhanmadao/' + key: Z / ('CommonModsV2/Export/SM_Zhanmadao_Blade_' + key + '_V2.fbx')
                for key in ['extended_edge', 'heavy_spine', 'feather_edge']})
sources.update({'zhanmadao/' + key: Z / ('TangDaoBladesV1/Export/SM_Zhanmadao_Blade_' + key + '_V1.fbx')
                for key in ['yanling_edge', 'tengyun_dragon']})
sources['zhanmadao/chixiao'] = Z / 'ChixiaoBladeV1/Export/SM_Zhanmadao_Blade_chixiao_V1.fbx'
sources['zhanmadao/zhufeng'] = Z / 'ZhufengBladeV1/Export/SM_Zhanmadao_Blade_zhufeng_V1.fbx'
sources.update({'tang_dao/' + key: S / ('TangDaoMeshy20261002/Export/SM_TangDao_Blade_' + key + '.fbx')
                for key in ['factory', 'extended_edge', 'heavy_spine', 'feather_edge']})
sources['tang_dao/yanling_edge'] = S / 'TangDaoMeshy20261002/YanlingBlade20261002/Export/SM_TangDao_Blade_yanling_edge.fbx'
sources['tang_dao/tengyun_dragon'] = S / 'TangDaoMeshy20261002/TengyunBlade20261002/Export/SM_TangDao_Blade_tengyun_dragon.fbx'
result = {}
for key, path in sources.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    objects = [o for o in objects if 'LOD0' in o.name] or objects
    triangles = []
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        points = np.asarray([tuple(v.co) for v in mesh.vertices]) * 100
        triangles.append(points[np.asarray([tuple(t.vertices) for t in mesh.loop_triangles])])
    tri = np.concatenate(triangles)
    low, high = float(tri[:, :, 2].min()), float(tri[:, :, 2].max())
    stations = np.linspace(low + .08 * (high - low), low + .96 * (high - low), 17)
    choice = key.split('/')[1]
    fraction, width_fraction = (.59, .46) if choice == 'chixiao' else (.56, .56) if choice == 'zhufeng' else (.50, .70)
    centers, widths = [], []
    for station in stations:
        cuts = []
        for a, b in [(0, 1), (1, 2), (2, 0)]:
            pa, pb = tri[:, a], tri[:, b]
            dz = pb[:, 2] - pa[:, 2]
            valid = (np.abs(dz) > 1e-8) & ((pa[:, 2] - station) * (pb[:, 2] - station) <= 0)
            t = (station - pa[valid, 2]) / dz[valid]
            cuts.append(pa[valid] + (pb[valid] - pa[valid]) * t[:, None])
        section = np.concatenate(cuts)
        left, right = float(section[:, 0].min()), float(section[:, 0].max())
        centers.append(left + fraction * (right - left))
        widths.append((right - left) * width_fraction)
    arc = np.r_[0, np.cumsum(np.hypot(np.diff(stations), np.diff(centers)))]
    # User choice: keep rune proportions and concentrate the panels mid-blade.
    # Existing decoration is handled by its surface keepout, not an upper-tip panel.
    start, end, center = (.28, .90, .60) if choice == 'tengyun_dragon' else (.34, .90, .62) if choice == 'yanling_edge' else (.18, .90, .56)
    z_start, z_end, z_center = [low + f * (high - low) for f in [start, end, center]]
    span_z = np.linspace(z_start, z_end, 25)
    reference_width = float(np.interp(span_z, stations, widths).min())
    result[key] = {'source': str(path), 'z_cm': stations.tolist(), 'center_x_cm': centers,
                   'width_cm': widths, 'arc_cm': arc.tolist(), 'blade_z_cm': [low, high],
                   'lane_u_center': fraction, 'lane_width_fraction': width_fraction,
                   'display_arc_cm': np.interp([z_start, z_end, z_center], stations, arc).tolist(),
                   'reference_width_cm': reference_width, 'preserve_rune_aspect': True}
(P / 'layouts.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print('DAO_LONGITUDINAL_LAYOUTS_AUTHORED', len(result))
