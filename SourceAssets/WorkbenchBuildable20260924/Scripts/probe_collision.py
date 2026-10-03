import unreal as u
import json

LOG = r'D:\FPS3D\FPSGAME\Saved\wb_collision_probe.log'
out = {}

# CollisionTraceFlag enum int -> name
CTF = {0: 'CTF_OFF', 1: 'CTF_SIMPLE_AS_SIMPLE', 2: 'CTF_COMPLEX_AS_SIMPLE', 3: 'CTF_USE_DEFAULT'}

def probe(tag, path):
    d = {'path': path}
    if not u.EditorAssetLibrary.does_asset_exist(path):
        d['missing'] = True
        out[tag] = d
        return d
    m = u.EditorAssetLibrary.load_asset(path)
    if not m:
        d['load_failed'] = True
        out[tag] = d
        return d
    try:
        bs = m.get_editor_property('body_setup')
        ctf = bs.get_editor_property('collision_trace_flag')
        # ctf may be an enum object or int
        try:
            ci = int(ctf)
        except Exception:
            ci = None
        d['collision_trace_flag_raw'] = str(ctf)
        d['collision_trace_flag_int'] = ci
        d['collision_trace_flag_name'] = CTF.get(ci, str(ctf))
    except Exception as e:
        d['body_setup_error'] = str(e)
    try:
        ns = m.get_editor_property('nanite_settings')
        d['nanite_enabled'] = bool(ns.get_editor_property('enabled'))
    except Exception as e:
        d['nanite_error'] = str(e)
    try:
        b = m.get_bounds()
        d['size_cm'] = [round(2 * b.box_extent.x, 1), round(2 * b.box_extent.y, 1), round(2 * b.box_extent.z, 1)]
    except Exception as e:
        d['bounds_error'] = str(e)
    try:
        d['num_source_models'] = len(m.get_source_models())
    except Exception as e:
        d['source_models_error'] = str(e)
    try:
        d['num_mats'] = len(m.get_materials())
    except Exception as e:
        pass
    out[tag] = d
    return d

probe('furnace', '/Game/Dungeons/AtmosphereV2/RoomInteriors/BlastFurnace/Meshes/SM_BlastFurnace.SM_BlastFurnace')
probe('workbench', '/Game/Building/Workbench/Meshes/SM_WBStandalone_Workbench.SM_WBStandalone_Workbench')

# Also resolve mesh paths straight from the active palette (ground truth of what placement uses).
try:
    pal = u.EditorAssetLibrary.load_asset('/Game/Building/DA_VoxelBuildPalette.DA_VoxelBuildPalette')
    entries = {}
    for c in pal.get_editor_property('components'):
        cid = str(c.get_editor_property('id'))
        mm = c.get_editor_property('mesh')
        fp = c.get_editor_property('footprint')
        if cid in ('blast_furnace', 'workbench_table'):
            entries[cid] = {'mesh': mm.get_path_name() if mm else None,
                            'footprint': [fp.x, fp.y, fp.z]}
    out['palette'] = entries
    for cid, info in entries.items():
        if info['mesh'] and cid not in out:
            probe('pal_' + cid, info['mesh'])
except Exception as e:
    out['palette_error'] = str(e)

with open(LOG, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print('WBPROBE_DONE')
