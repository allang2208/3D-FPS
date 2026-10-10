"""Capture only the current player's staff/hand for the requested grip diagnosis."""
import json
from pathlib import Path
import unreal as u
root=Path('D:/FPS3D/FPSGAME')
out=root/'SourceAssets/ThirdPersonStaffGripFacing20261009'
out.mkdir(parents=True,exist_ok=True)
def pack(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result={'game_world':str(world),'bodies':[]}
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        body=actor.get_component_by_class(u.FPSPlayerBodyComponent)
        if not body:continue
        mesh=body.get_body_mesh()
        if not mesh:continue
        state=body.get_body_state()
        record={'actor':actor.get_name(),'mesh':mesh.skeletal_mesh_asset.get_path_name(),
                'family':str(state.family),'action':str(state.action),'variant':str(state.action_variant),
                'world':pack(mesh.get_world_transform()),'bones':{},'components':[]}
        for i in range(mesh.get_num_bones()):
            n=str(mesh.get_bone_name(i))
            record['bones'][n]=pack(mesh.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT))
        for c in actor.get_components_by_class(u.MeshComponent):
            asset=c.skeletal_mesh_asset if isinstance(c,u.SkeletalMeshComponent) else c.static_mesh if isinstance(c,u.StaticMeshComponent) else None
            if asset:
                record['components'].append({'name':c.get_name(),'asset':asset.get_path_name(),
                    'visible':c.is_visible(),'world':pack(c.get_world_transform()),
                    'materials':[str(c.get_material(i)) for i in range(c.get_num_materials())]})
        result['bodies'].append(record)
(out/'existing-scene.json').write_text(json.dumps(result,indent=2))
print('STAFF_FACING_SCENE '+str(len(result['bodies']))+' bodies; '+str(world))
