import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent
def tf(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
rows={}
paths={
 'm4':'/Game/Weapons/M4ContactImpactFinal/A_AKM_idle',
 'svd':'/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_idle',
 'm24':'/Game/Weapons/M24/Repair20261027/Animations/A_M24_idle',
}
for name,path in paths.items():
    clip=u.load_asset(path);opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,opts)
    ref=u.AnimPoseExtensions.get_reference_pose(clip.get_editor_property('skeleton'))
    bones=list(map(str,u.AnimPoseExtensions.get_bone_names(pose)))
    rows[name]={'clip':clip.get_path_name(),'seconds':clip.get_play_length(),
      'world':{n:tf(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in bones},
      'local':{n:tf(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in bones},
      'rest_world':{n:tf(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD)) for n in bones}}
profile=u.load_asset('/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/DA_SVCH_ElbowFitGrip')
if profile:
    rows['svch_profile']=[]
    for c in profile.get_editor_property('clips'):
        base=c.get_editor_property('base');retained=c.get_editor_property('retained')
        if 'idle' not in base.get_name():continue
        rows['svch_profile'].append({'base':base.get_path_name(),'retained':retained.get_path_name() if retained else None,
          'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),
          'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]})
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
rows['live']=[]
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if 'FPSGAMECharacter' not in actor.get_class().get_name():continue
        row={'actor':actor.get_path_name(),'parts':[]}
        for c in actor.get_components_by_class(u.SkeletalMeshComponent):
            mesh=c.get_editor_property('skeletal_mesh_asset')
            if mesh and '/Weapons/M24/' in mesh.get_path_name():
                row['parts'].append({'mesh':mesh.get_path_name(),'relative':tf(c.get_relative_transform()),
                    'world':tf(c.get_world_transform()),'visible':c.is_visible()})
        if row['parts']:rows['live'].append(row)
(O/'ue_inputs.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('M24_HOLD_INPUTS',[(k,v.get('seconds')) for k,v in rows.items() if isinstance(v,dict)],'live',rows['live'])
