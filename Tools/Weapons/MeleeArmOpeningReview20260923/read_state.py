"""Read loaded animation versions and current camera/weapon state without edits."""
import json, hashlib
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Saved/MeleeArmOpeningReview20260923'
OUT.mkdir(parents=True,exist_ok=True)
def path(o): return o.get_path_name() if o else None
def transform(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.w,q.x,q.y,q.z],'s':[s.x,s.y,s.z]}
receipt=json.loads((ROOT/'SourceAssets/MeleeArmOpening20260923/install_receipt.json').read_text())
report={'saved_assets':{},'game':None}
for name,record in receipt['saved'].items():
    asset=u.load_asset(record['asset'])
    disk=ROOT/'Content'/(record['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
    patch=json.loads((ROOT/'SourceAssets/MeleeArmOpening20260923'/name).with_suffix('.json').read_text())
    options=u.AnimPoseEvaluationOptions()
    options.evaluation_type=u.AnimDataEvalType.SOURCE
    maximum=0.
    for index in (len(patch['samples'])//3,len(patch['samples'])//2):
        row=patch['samples'][index]
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,row['seconds'],options)
        for bone in patch['edited_bones']:
            actual=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.LOCAL)
            expected=u.Vector(*row['bones'][bone]['p'])
            maximum=max(maximum,(actual.translation-expected).length())
    report['saved_assets'][name]={'path':path(asset),'revision':u.EditorAssetLibrary.get_metadata_tag(asset,'ArmOpening.Revision'),
        'disk_matches_receipt':hashlib.sha256(disk.read_bytes()).hexdigest()==record['saved_sha256'],
        'loaded_track_position_error_cm':maximum}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_game_world()
report['editor_world']=path(editor.get_editor_world())
report['game_world']=path(world)
if world:
    pawn=u.GameplayStatics.get_player_pawn(world,0)
    report['game']={'pawn':path(pawn),'components':[]}
    if pawn:
        camera=pawn.get_component_by_class(u.CameraComponent)
        report['game']['camera']={'path':path(camera),'transform':transform(camera.get_world_transform()),
            'fov':camera.field_of_view,'aspect':camera.aspect_ratio,'axis':str(camera.get_editor_property('aspect_ratio_axis_constraint'))}
        for component in pawn.get_components_by_class(u.SkeletalMeshComponent):
            report['game']['components'].append({'path':path(component),'mesh':path(component.get_editor_property('skeletal_mesh_asset')),
                'visible':component.is_visible(),'transform':transform(component.get_world_transform())})
        sword=pawn.get_component_by_class(u.RuneSwordComponent)
        if sword:
            report['game']['sword']={'equipped':sword.is_equipped(),'busy':sword.is_busy(),
                'clip':path(sword.get_editor_property('current_animation')),
                'animations':{str(n):path(a) for n,a in sword.get_editor_property('animations').items()}}
(OUT/'loaded-state.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
