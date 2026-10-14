"""Read the existing pawn's sword/body frames without changing play or assets."""
import json
from pathlib import Path
import unreal as u

out=Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonSwordStairs20261005')
out.mkdir(parents=True,exist_ok=True)
def path(x):return x.get_path_name() if x else None
def tf(t):
    p,q=t.translation,t.rotation
    return {'p':[p.x,p.y,p.z],'q':[q.x,q.y,q.z,q.w]}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result={'world':path(world),'pawns':[]}
if world:
    for pawn in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
        adapter=pawn.get_component_by_class(u.FPSPlayerBodyComponent)
        item={'state':adapter.get_body_state().export_text(),'meshes':[]}
        for mesh in pawn.get_components_by_class(u.SkeletalMeshComponent):
            if mesh!=pawn.mesh and 'Sword' not in mesh.get_name() and mesh.get_class().get_name()!='FPSBodyWeaponMeshComponent':continue
            asset=mesh.get_skeletal_mesh_asset()
            if not asset:continue
            bones=[str(b) for b in mesh.get_all_socket_names() if str(b) in ('root','pelvis','spine_01','spine_03','head','WPN_root') or str(b).startswith(('clavicle','upperarm','lowerarm','hand_'))]
            ref=asset.skeleton.get_reference_pose()
            item['meshes'].append({'name':mesh.get_name(),'asset':path(asset),'frame':tf(mesh.get_world_transform()),
                'post_process':path(mesh.get_post_process_instance()),
                'pose':{b:tf(mesh.get_socket_transform(b,u.RelativeTransformSpace.RTS_COMPONENT)) for b in bones},
                'reference':{b:tf(u.AnimPoseExtensions.get_bone_pose(ref,b,u.AnimPoseSpaces.WORLD)) for b in bones},
                'parents':{b:str(mesh.get_parent_bone(b)) for b in bones}})
        result['pawns'].append(item)
(out/'before.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('SWORD_STAIR_STATE '+json.dumps({'world':result['world'],'pawns':[{'state':p['state'][:300],'meshes':[m['name'] for m in p['meshes']]} for p in result['pawns']]}))
