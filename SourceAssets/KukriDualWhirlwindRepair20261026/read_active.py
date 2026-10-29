"""Read the active dual take and the current session's visible equipment."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/KukriDualWhirlwindRepair20261026'
config=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
source=ROOT/'SourceAssets/KukriDualWhirlwind20261026'
version=globals().get('READ_VERSION','before')
saved=json.loads((OUT/'assets-saved.json').read_text()) if version=='after' else None
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
result={}
for label in ('jason','kaitlin'):
    active=config if label=='jason' else config['body_variants'][label]
    mesh=u.load_asset(active['body_mesh'])
    names=json.loads((source/(label+'-actions.json')).read_text())['names']
    opts=u.AnimPoseEvaluationOptions()
    opts.optional_skeletal_mesh=mesh
    opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
    clips={}
    for stage in ('Start','Loop','End'):
        role='Dual.Whirlwind.'+stage
        path=(saved['bodies'][label]['clips'] if saved else active['clips'])['Kukri.FullBody.'+role]
        clip=u.load_asset(path);length=clip.get_play_length();n=max(1,round(length*120))
        times=[length*k/n for k in range(n+1)]
        frames=[]
        for t in times:
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opts)
            frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in names])
        clips[role]={'asset':path,'duration':length,'times':times,'world':frames}
    result[label]={'mesh':mesh.get_path_name(),'names':names,'clips':clips}
(OUT/(version+'-compressed.json')).write_text(json.dumps(result,separators=(',',':')))
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_game_world() if editor else None
session={'game_world':world.get_path_name() if world else None,'characters':[]}
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        row={'actor':actor.get_path_name(),'meshes':[]}
        for comp in actor.get_components_by_class(u.SkeletalMeshComponent):
            mesh=comp.get_skeletal_mesh_asset()
            if mesh:
                row['meshes'].append({'component':comp.get_name(),'mesh':mesh.get_path_name(),'visible':comp.is_visible()})
        session['characters'].append(row)
(OUT/'current-session.json').write_text(json.dumps(session,indent=2))
print('DUAL_REPAIR_ACTIVE_POSES_READ')
print(json.dumps(session,separators=(',',':')))
