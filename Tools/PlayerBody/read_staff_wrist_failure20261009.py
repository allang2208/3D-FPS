"""Read an already-running scene for the reported wrist deformation. No play/start."""
import json
from pathlib import Path
import unreal as u
out=Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonStaffWrist20261009')
out.mkdir(parents=True,exist_ok=True)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result={'game_world':str(world),'bodies':[]}
def pack(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        body=actor.get_component_by_class(u.FPSPlayerBodyComponent)
        if not body:continue
        mesh=body.get_body_mesh()
        if not mesh:continue
        state=body.get_body_state();anim=mesh.get_anim_instance()
        bones=['clavicle_r','upperarm_r','lowerarm_r','hand_r','index_metacarpal_r','middle_metacarpal_r','index_01_r','middle_01_r','thumb_01_r']
        record={'actor':actor.get_name(),'mesh':mesh.skeletal_mesh_asset.get_path_name(),'action':str(state.action),'family':str(state.family),'variant':str(state.action_variant),'progress':state.action_progress,'bones':{n:pack(mesh.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in bones}}
        if anim:
            try:record['grip_q']=str(anim.get_editor_property('staff_hand_rotation'))
            except Exception:pass
        result['bodies'].append(record)
(out/'existing-scene.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,separators=(',',':')))
