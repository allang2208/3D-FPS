"""Read the saved bow action and current camera setup for the reported missing grab."""
import unreal as u, json
from pathlib import Path
P=Path(__file__).parent
mesh=u.load_asset('/Game/Weapons/DarkBow20260925/ContactV9/SK_Bow_BareArmsV7')
clip=u.load_asset('/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat')
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh
opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.should_retarget=True
def vec(v):return [v.x,v.y,v.z]
def tf(v):return {'p':vec(v.translation),'q':[v.rotation.x,v.rotation.y,v.rotation.z,v.rotation.w],'s':vec(v.scale3d)}
out={'clip':clip.get_path_name(),'length':clip.get_play_length(),'poses':[], 'live':[]}
for t in (0.,.05,.07,.10,.115,.14,.18,.22,.26,.32,.44,.62,.9):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt)
    names=u.AnimPoseExtensions.get_bone_names(pose)
    out['poses'].append({'t':t,'bones':{str(n):tf(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}})
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
player=u.GameplayStatics.get_player_character(w,0) if w else None
if player:
    for c in player.get_components_by_class(u.SceneComponent):
        if 'Bow' in c.get_name() or isinstance(c,u.CameraComponent):
            row={'name':c.get_name(),'visible':c.is_visible(),'relative':tf(c.get_relative_transform())}
            if isinstance(c,u.CameraComponent):row['fov']=c.field_of_view
            out['live'].append(row)
(P/'imported-before.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'clip':out['clip'],'length':out['length'],'live':out['live'],'pose_count':len(out['poses'])}))
