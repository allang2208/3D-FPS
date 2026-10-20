"""Read only the collision/health defaults of the reported comparison target."""
import json
from pathlib import Path
import unreal as u

rows = {}
for name in ('NightWarden', 'NurseZombie', 'HandBrain'):
    cls = u.EditorAssetLibrary.load_blueprint_class(f'/Game/Monsters/{name}/BP_{name}')
    cdo = u.get_default_object(cls)
    parts = []
    for component in cdo.get_components_by_class(u.ActorComponent):
        row = {'name': component.get_name(), 'class': component.get_class().get_name()}
        if isinstance(component, u.PrimitiveComponent):
            row['collision_enabled'] = str(component.get_collision_enabled())
            row['visibility_response'] = str(component.get_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY))
        if isinstance(component, u.SkeletalMeshComponent):
            row['mesh'] = component.skeletal_mesh_asset.get_path_name() if component.skeletal_mesh_asset else None
            physics = component.get_editor_property('physics_asset_override')
            if not physics and component.skeletal_mesh_asset:
                physics = component.skeletal_mesh_asset.get_editor_property('physics_asset')
            row['physics_asset'] = physics.get_path_name() if physics else None
        parts.append(row)
    rows[name] = parts
Path(__file__).with_name('target_defaults.json').write_text(json.dumps(rows, indent=2))
print('SVCH_COMPARISON_TARGET_DEFAULTS_READ')
