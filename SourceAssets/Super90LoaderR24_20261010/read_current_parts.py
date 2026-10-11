"""Read the reported rack components without changing or running the scene."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent
root='/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7'
mesh=u.load_asset(root)
data={'mesh':root,'materials':[],'components':[]}
for m in mesh.get_editor_property('materials'):
    mat=m.get_editor_property('material_interface')
    data['materials'].append({'slot':str(m.get_editor_property('material_slot_name')),'material':mat.get_path_name() if mat else None})
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        for c in actor.get_components_by_class(u.SkeletalMeshComponent):
            asset=c.get_skinned_asset()
            if not asset:continue
            if 'Super90' not in asset.get_path_name() and 'Gauntlet' not in asset.get_path_name():continue
            row={'component':c.get_name(),'asset':asset.get_path_name(),'visible':c.is_visible(),'materials':[]}
            for i in range(c.get_num_materials()):
                material=c.get_material(i)
                row['materials'].append({'index':i,'material':material.get_path_name() if material else None})
            data['components'].append(row)
(O/'current_parts.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('SUPER90_CURRENT_PARTS',json.dumps(data),flush=True)
