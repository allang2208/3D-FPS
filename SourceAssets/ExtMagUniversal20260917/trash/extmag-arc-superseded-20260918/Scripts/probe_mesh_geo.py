import unreal as u, json
out = {}
for name, path in {
    "ExtMag": "/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_Universal",
    "DrumOld": "/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_LargeDrum",
}.items():
    m = u.load_asset(path)
    if not m:
        out[name] = "MISSING"; continue
    lod = u.EditorStaticMeshLibrary.get_lod_count(m)
    info = {"lods": lod,
            "verts_lod0": u.EditorStaticMeshLibrary.get_number_verts(m, 0),
            "mats": len(m.get_editor_property('static_materials'))}
    # raw mesh description triangle count
    try:
        md = m.get_editor_property('source_models')[0].mesh_description if hasattr(m.get_editor_property('source_models')[0], 'mesh_description') else None
    except Exception as e:
        info['md_err'] = str(e)[:80]
    out[name] = info
u.log("EXTMAG_GEO_PROBE " + json.dumps(out))
