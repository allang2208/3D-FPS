"""Reapply saved Material21 bindings after a 201 geometry/material reimport."""
from pathlib import Path
import json
import unreal as u


def apply():
    manifest = Path(__file__).with_name('bindings.json')
    if not manifest.exists(): return []
    data = json.loads(manifest.read_text(encoding='utf8'))
    saved = []
    for path, info in data['meshes'].items():
        mesh = u.load_asset(path)
        if not mesh: continue
        prop = 'materials' if isinstance(mesh, u.SkeletalMesh) else 'static_materials'
        slots = mesh.get_editor_property(prop)
        changed = False
        for i, slot in enumerate(slots):
            desired = info.get(str(slot.material_slot_name))
            if not desired: continue
            if slot.material_interface and slot.material_interface.get_path_name() == desired: continue
            mat = u.load_asset(desired)
            if not mat: raise RuntimeError('Missing saved Material21 material ' + desired)
            slot.material_interface = mat
            slots[i] = slot
            changed = True
        if changed:
            mesh.set_editor_property(prop, slots)
            if not u.EditorAssetLibrary.save_loaded_asset(mesh, False): raise RuntimeError('Cannot save ' + path)
            saved.append(path)
    return saved


if __name__ == '__main__':
    apply()
