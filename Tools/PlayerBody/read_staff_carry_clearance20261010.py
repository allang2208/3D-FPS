"""Read the user's existing scene and staff/book mounts; do not start play."""
import json
from pathlib import Path
import unreal as u

out=Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonStaffCarryClearance20261010')
out.mkdir(parents=True,exist_ok=True)
def pack(t):
    return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result={'world':str(world),'actors':[]}
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        body=actor.get_component_by_class(u.FPSPlayerBodyComponent)
        if not body:continue
        mesh=body.get_body_mesh()
        if not mesh:continue
        state=body.get_body_state()
        row={'name':actor.get_name(),'mesh':mesh.skeletal_mesh_asset.get_path_name(),
             'component':pack(mesh.get_world_transform()),'family':str(state.family),
             'action':str(state.action),'variant':str(state.action_variant),'bones':{},'parts':[]}
        for n in ['pelvis','spine_01','spine_03','spine_05','clavicle_r','upperarm_r','lowerarm_r','hand_r',
                  'clavicle_l','upperarm_l','lowerarm_l','hand_l','thigh_r','thigh_l']:
            row['bones'][n]=pack(mesh.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT))
        for part in actor.get_components_by_class(u.StaticMeshComponent):
            parent=part.get_attach_parent()
            if parent!=mesh:continue
            asset=part.static_mesh
            row['parts'].append({'component':part.get_name(),'mesh':asset.get_path_name() if asset else None,
                'socket':str(part.get_attach_socket_name()),'relative':pack(part.get_relative_transform()),
                'world':pack(part.get_world_transform()),'visible':part.is_visible(),
                'bounds':str(asset.get_bounds()) if asset else None})
        result['actors'].append(row)
(out/'existing-scene.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('STAFF_CARRY_SCENE',json.dumps(result,separators=(',',':')))
