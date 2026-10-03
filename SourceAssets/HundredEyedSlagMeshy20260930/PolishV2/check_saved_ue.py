"""Focused fresh-process readback of the reported UE defects; no map edits or PIE."""
import unreal as u,json
from pathlib import Path
OUT=Path(__file__).resolve().parent;DEST='/Game/Monsters/HundredEyedSlag/PolishV2'
actor=u.get_default_object(u.HundredEyedSlagMonster)
mesh=actor.get_editor_property('visual_mesh')
if not mesh or mesh.get_path_name()!=DEST+'/SK_HundredEyedSlag_V2.SK_HundredEyedSlag_V2':raise RuntimeError('Native F6 class is not using the revised mesh')
clips=actor.get_editor_property('clips')
report={'mesh':mesh.get_path_name(),'chase_speed':actor.get_editor_property('chase_speed'),
    'return_speed':actor.get_editor_property('return_speed'),'ragdoll_handoff_seconds':actor.get_editor_property('ragdoll_handoff_seconds'),
    'physics_asset':mesh.get_editor_property('physics_asset').get_path_name(),'clips':{}}
for role in ('Run','Move','Death'):
    clip=clips[role]
    if not clip or not clip.get_path_name().startswith(DEST+'/Animations/'):raise RuntimeError('Native class is not using V2 '+role)
    report['clips'][role]={'path':clip.get_path_name(),'seconds':clip.get_play_length()}
material=list(mesh.get_editor_property('materials'))[0].material_interface
if not u.PoisonMaggotMonster.compile_material_assets([material]):raise RuntimeError('Skin recompile failed')
report['skin_material']=material.get_path_name()
report['skin_textures']=[t.get_path_name() for t in u.MaterialEditingLibrary.get_material_used_textures(material)]
if len(report['skin_textures'])!=4:raise RuntimeError('Saved skin still does not use four PBR maps')
if report['chase_speed']!=280 or report['return_speed']!=120:raise RuntimeError('Incorrect native movement defaults')
if abs(report['ragdoll_handoff_seconds']-.42)>.001:raise RuntimeError('Incorrect ragdoll timing')
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
pose=u.AnimPoseExtensions.get_anim_pose_at_time(clips['Run'],0.,options)
report['run_bones']=[str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)]
if 'front_palm_R' not in report['run_bones']:raise RuntimeError('Imported right palm bone mismatch')
report.update(stage='native_defaults_saved_assets_skin_and_animation_references_checked',pie_tested=False,ragdoll_runtime_tested=False)
(OUT/'saved_ue_checks.json').write_text(json.dumps(report,indent=2))
u.log('SLAG_SAVED_READBACK '+json.dumps(report))
