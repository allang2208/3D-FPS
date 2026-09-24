"""Probe crate SKs v2: slot materials + geometry via whatever render-data API this build exposes.

Writes probes/crate_top.json. Never hard-fails: optional APIs are discovered from dir(mesh).
"""
import json
import unreal as u

MESHES = {
    'source': '/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigid',
    'T1': '/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T1_Wood',
    'T2': '/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T2_StoneWood',
    'T3': '/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T3_Iron',
    'T4': '/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T4_IronGold',
    'T5': '/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T5_SilverGem',
}
out = {'meshes': {}, 'materials': {}, 'api': {}}

def mat_flags(mi):
    if mi is None:
        return None
    key = mi.get_path_name()
    if key not in out['materials']:
        rec = {'class': mi.get_class().get_name()}
        base = mi if isinstance(mi, u.Material) else mi.get_editor_property('parent')
        if base is not None:
            try:
                rec['two_sided'] = bool(base.get_editor_property('two_sided'))
            except Exception as exc:
                rec['two_sided_err'] = str(exc)
            try:
                rec['blend'] = str(base.get_editor_property('blend_mode'))
            except Exception:
                pass
        out['materials'][key] = rec
    return key

def try_call(label, fn, *args):
    try:
        v = fn(*args)
        out['api'].setdefault('ok', []).append('%s%s=%s' % (label, args, v))
        return int(v)
    except Exception as exc:
        out['api'].setdefault('fail', []).append('%s%s: %s' % (label, args, str(exc)[:90]))
        return None

for tag, path in MESHES.items():
    mesh = u.load_asset(path)
    if mesh is None:
        out['meshes'][tag] = {'missing': True}
        continue
    if not out['api'].get('mesh_dir'):
        out['api']['mesh_dir'] = [a for a in dir(mesh) if ('lod' in a or 'section' in a or 'tri' in a or 'material' in a or 'bound' in a) and not a.startswith('_')]
    rec = {}
    slots = []
    for s in mesh.get_editor_property('materials'):
        name = str(s.get_editor_property('material_slot_name'))
        mi = s.get_editor_property('material_interface')
        slots.append({'slot': name, 'mat': mat_flags(mi)})
    rec['slots'] = slots
    try:
        rec['bounds'] = str(mesh.get_bounds())
    except Exception as exc:
        rec['bounds_err'] = str(exc)[:120]
    nsec = None
    for m in ('get_num_sections', 'get_section_count'):
        if hasattr(mesh, m):
            nsec = try_call(m, getattr(mesh, m), 0)
            if nsec is None:
                nsec = try_call(m, getattr(mesh, m))
            if nsec is not None:
                break
    lodtri = try_call('get_lod_number_of_triangles', getattr(mesh, 'get_lod_number_of_triangles', None) or (lambda l: None), 0)
    rec['lod0_tri'] = lodtri
    table = []
    if nsec:
        for i in range(nsec):
            row = {'i': i}
            for m in ('get_number_of_triangles_for_section',):
                if hasattr(mesh, m):
                    v = try_call(m, getattr(mesh, m), i, 0)
                    if v is None:
                        v = try_call(m + '1', getattr(mesh, m), i)
                    if v is not None:
                        row['tri'] = v
                        break
            for m in ('get_material_index_for_section', 'get_material_index'):
                if hasattr(mesh, m):
                    v = try_call(m, getattr(mesh, m), i, 0)
                    if v is None:
                        v = try_call(m + '1', getattr(mesh, m), i)
                    if v is not None:
                        row['mat'] = v
                        break
            table.append(row)
    rec['sections'] = table
    out['meshes'][tag] = rec

with open(r'D:\FPS3D\FPSGAME\SourceAssets\WarehouseCrateTiers20260924\probes\crate_top.json', 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print('CRATE_TOP_DONE', flush=True)
