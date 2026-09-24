"""Probe v3: find per-section vertex/triangle truth for the crate SKs.

Tries: (a) USkeletalMesh.imported_asset source model (UStaticMesh with sections),
(b) full dir() dump so we stop guessing APIs.
Writes probes/crate_sections.json.
"""
import json
import unreal as u

MESHES = {
    'source': '/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigid',
    'T1': '/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T1_Wood',
}
out = {}
for tag, path in MESHES.items():
    mesh = u.load_asset(path)
    rec = {'dir': sorted(a for a in dir(mesh) if not a.startswith('_'))}
    for prop in ('imported_asset', 'source_model', 'skeleton', 'bounds'):
        try:
            v = mesh.get_editor_property(prop)
            rec['has_' + prop] = str(v)[:120] if v is not None else None
        except Exception as exc:
            rec['has_' + prop] = 'ERR ' + str(exc)[:80]
    try:
        src = mesh.get_editor_property('imported_asset')
        if src is not None:
            srec = {'class': src.get_class().get_name(), 'dir': sorted(a for a in dir(src) if 'lod' in a.lower() or 'section' in a.lower() or 'tri' in a.lower() or 'vert' in a.lower())}
            for m in ('get_lod_number_of_triangles', 'get_lod_number_of_vertices', 'get_num_sections', 'get_number_of_triangles_for_section', 'get_material_index_for_section'):
                if hasattr(src, m):
                    try:
                        srec[m] = 'present'
                    except Exception:
                        pass
            rec['source'] = srec
    except Exception as exc:
        rec['source_err'] = str(exc)[:120]
    out[tag] = rec

with open(r'D:\FPS3D\FPSGAME\SourceAssets\WarehouseCrateTiers20260924\probes\crate_sections.json', 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print('CRATE_SECTIONS_DONE', flush=True)
