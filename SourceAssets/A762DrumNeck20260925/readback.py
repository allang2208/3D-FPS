"""Read back the shipping drum asset: which FBX it came from, its slot layout and
its bounds, so the on-disk asset can be tied to this round's rebuild."""
import json
import unreal as u
from pathlib import Path

O = Path(__file__).parent
mesh = u.load_asset('/Game/Weapons/A762/Accessories05/Meshes/SM_A762_drum')
if not mesh:
    raise RuntimeError('missing drum asset')
data = mesh.get_editor_property('asset_import_data')
src = list(data.extract_filenames()) if data else []
bounds = mesh.get_bounds()
out = {
    'asset': mesh.get_path_name(),
    'import_sources': src,
    'slots': [str(s.material_slot_name) for s in mesh.static_materials],
    'materials': [s.material_interface.get_path_name() if s.material_interface else None
                  for s in mesh.static_materials],
    'bbox_extent_cm': [round(bounds.box_extent.x, 3), round(bounds.box_extent.y, 3), round(bounds.box_extent.z, 3)],
    'bbox_origin_cm': [round(bounds.origin.x, 3), round(bounds.origin.y, 3), round(bounds.origin.z, 3)],
}
(O / 'readback.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('DRUM_READBACK', json.dumps(out), flush=True)
