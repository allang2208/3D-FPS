"""Keep the published M4 finish when its existing meshes are reimported."""
import json
import re
from pathlib import Path
import unreal as u

MANIFEST = Path(__file__).with_name('current_surface_bindings.json')


def apply_current_bindings(mesh):
    if not MANIFEST.exists():
        return 0
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    bindings = data['meshes'].get(mesh.get_path_name(), {})
    if not bindings:
        return 0
    canonical = lambda name: re.sub(r'[._]\d{3}$', '', name)
    prop = 'materials' if isinstance(mesh, u.SkeletalMesh) else 'static_materials'
    slots = list(mesh.get_editor_property(prop))
    count = 0
    for index, slot in enumerate(slots):
        name = str(slot.material_slot_name)
        target = bindings.get(name)
        if not target:
            candidates = {path for key, path in bindings.items() if canonical(key) == canonical(name)}
            if len(candidates) == 1:
                target = candidates.pop()
        if target:
            material = u.load_asset(target)
            if not material:
                raise RuntimeError('Missing published M4 material ' + target)
            slot.material_interface = material
            slots[index] = slot
            count += 1
    if count:
        mesh.set_editor_property(prop, slots)
        u.EditorAssetLibrary.set_metadata_tag(mesh, 'M4SurfaceFinishRevision', data['version'])
    return count
