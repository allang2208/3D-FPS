"""Read current body/clip identity and pose without driving gameplay."""
import json
from pathlib import Path
import unreal as u

root=Path('D:/FPS3D/FPSGAME')
out=root/'SourceAssets/ThirdPersonDashArm20261010'
out.mkdir(parents=True,exist_ok=True)
config=json.loads((root/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
report={'configured_dash':config['clips']['Melee.FullBody.DashOverhead'],'bodies':[]}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report['pie_active']=bool(world)
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        body=actor.get_component_by_class(u.FPSPlayerBodyComponent)
        if not body:continue
        mesh=body.get_body_mesh()
        if not mesh:continue
        state=body.get_body_state();anim=mesh.get_anim_instance()
        row={'actor':actor.get_name(),'mesh':mesh.skeletal_mesh_asset.get_path_name(),
             'state':{k:str(state.get_editor_property(k)) for k in ('family','weapon','action','action_variant','action_progress','action_weight','contact_fraction','release_fraction')},
             'bones':{}}
        for i in range(mesh.get_num_bones()):
            name=mesh.get_bone_name(i)
            row['bones'][str(name)]=pack(mesh.get_socket_transform(name,u.RelativeTransformSpace.RTS_COMPONENT))
        row['clips']={str(k):v.get_path_name() for k,v in anim.get_editor_property('clips').items() if str(k).startswith('Melee.FullBody.') and v}
        report['bodies'].append(row)
(out/'live-before.json').write_text(json.dumps(report,indent=2))
print('DASH_ARM_LIVE '+json.dumps({**report,'bodies':[{k:v for k,v in r.items() if k!='bones'} for r in report['bodies']]}))
