"""Read the loaded production inputs needed for the requested UV repair."""
import unreal as u
import json
from pathlib import Path

O = Path(__file__).parent
L = u.MaterialEditingLibrary
mesh = u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
def material(m):
    if not m:
        return None
    r = {'path': m.get_path_name()}
    if isinstance(m, u.MaterialInstanceConstant):
        r['parent'] = m.parent.get_path_name()
        r['scalars'] = {str(n): L.get_material_instance_scalar_parameter_value(m, n)
                        for n in ('SourceColorWeight', 'MaskUVChannel', 'Metallic', 'Roughness')}
        r['textures'] = {str(n): (t.get_path_name() if t else None)
                         for n in L.get_texture_parameter_names(m)
                         for t in [L.get_material_instance_texture_parameter_value(m, n)]}
    return r
world = u.EditorLevelLibrary.get_game_world()
data = {'pie': bool(world), 'slots': [{'name': str(s.material_slot_name), 'material': material(s.material_interface)} for s in mesh.materials], 'components': []}
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
        for c in actor.get_components_by_class(u.SkeletalMeshComponent):
            if c.skeletal_mesh_asset == mesh:
                data['components'].append({'actor': actor.get_name(), 'component': c.get_name(), 'materials': [material(c.get_material(i)) for i in range(c.get_num_materials())]})
(O / 'current_inputs.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
print('SUPER90_CURRENT_INPUTS', json.dumps({'pie': data['pie'], 'slots': len(data['slots']), 'components': len(data['components'])}))
