import unreal as u, json
out = {}
for name, path in {
    "AKM": "/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_drum",
    "QBZ": "/Game/Weapons/QBZ191/Attachments20260913/SM_QBZ191_drum",
    "M4": "/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_LargeDrum",
}.items():
    m = u.load_asset(path)
    if not m:
        out[name] = "MISSING"
        continue
    slots = []
    for s in m.get_editor_property('static_materials'):
        mi = s.material_interface
        slots.append({"slot": str(s.material_slot_name), "mat": mi.get_path_name() if mi else None})
    out[name] = {"path": m.get_path_name(), "slots": slots,
                 "bounds": str(m.get_bounds())}
u.log("DRUM_PROBE " + json.dumps(out))
