"""Read the imported source mesh and action catalogue; no target writes."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
BASE = '/Game/ParagonRampage/Characters/Heroes/Rampage'
mesh = u.load_asset(BASE + '/Meshes/Rampage')
if not isinstance(mesh, u.SkeletalMesh):
    raise RuntimeError('Imported Rampage source mesh is required')
component = u.SkeletalMeshComponent()
component.set_skeletal_mesh_asset(mesh)
bones = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
catalogue = []
for data in u.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(BASE + '/Animations', recursive=True):
    if str(data.asset_class_path.asset_name) != 'AnimSequence':
        continue
    name = str(data.asset_name)
    if not any(k in name.lower() for k in ('melee', 'smash', 'idle', 'jog_quad_fwd')):
        continue
    clip = data.get_asset()
    catalogue.append({'name': name, 'path': clip.get_path_name(), 'seconds': clip.get_play_length(),
        'additive': str(clip.get_editor_property('additive_anim_type'))})
report = {'mesh': mesh.get_path_name(), 'bones': bones,
          'parents': {b: str(component.get_parent_bone(b)) for b in bones}, 'actions': catalogue}
(ROOT / 'imported_catalogue.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'bones': bones, 'actions': catalogue}), flush=True)
