import unreal as u
import json

LOG = r'D:\FPS3D\FPSGAME\Saved\wb_collision_probe2.log'
out = {}

def dump(tag, path):
    d = {'path': path}
    if not path or not u.EditorAssetLibrary.does_asset_exist(path):
        d['missing'] = True
        out[tag] = d
        return d
    m = u.EditorAssetLibrary.load_asset(path)
    if not m:
        d['load_failed'] = True
        out[tag] = d
        return d
    d['collision_attrs'] = [a for a in dir(m) if 'collision' in a.lower()]
    for prop in ('b_has_nanite_support', 'b_valid_nanite_mesh_description'):
        try:
            d[prop] = m.get_editor_property(prop)
        except Exception:
            pass
    bs = m.get_editor_property('body_setup')
    d['body_setup_attrs'] = [a for a in dir(bs) if 'collision' in a.lower() or 'complex' in a.lower()]
    for prop in ('collision_trace_flag', 'b_use_complex_as_simple', 'b_collision_complex_source_from_high_res',
                 'b_suppress_simple_collision', 'b_use_simple_as_complex'):
        try:
            d['bs.' + prop] = str(bs.get_editor_property(prop))
        except Exception:
            pass
    try:
        ag = bs.get_editor_property('agg_geom')
        d['bs.agg_geom.convex_elements'] = len(ag.get_editor_property('convex_elements'))
        for box_prop in ('box_elements', 'sphere_elements', 'capsule_elements'):
            d['bs.agg_geom.' + box_prop] = len(ag.get_editor_property(box_prop))
    except Exception as e:
        d['agg_geom_error'] = str(e)
    try:
        b = m.get_bounds()
        d['size_cm'] = [round(2 * b.box_extent.x, 1), round(2 * b.box_extent.y, 1), round(2 * b.box_extent.z, 1)]
    except Exception:
        pass
    out[tag] = d
    return d

pal = u.EditorAssetLibrary.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette.DA_VoxelBuildPalette')
meshes = {}
for c in pal.get_editor_property('components'):
    cid = str(c.get_editor_property('id'))
    if cid in ('blast_furnace', 'workbench_table'):
        mm = c.get_editor_property('mesh')
        fp = c.get_editor_property('footprint')
        mount = str(c.get_editor_property('mount'))
        meshes[cid] = mm.get_path_name() if mm else None
        out.setdefault('palette', {})[cid] = {'mesh': meshes[cid], 'footprint': [fp.x, fp.y, fp.z], 'mount': mount}
for cid in ('blast_furnace', 'workbench_table'):
    if cid in meshes:
        dump(cid, meshes[cid])

with open(LOG, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('WBPROBE2_DONE')
