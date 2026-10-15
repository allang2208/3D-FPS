import json,unreal as u
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/FurnaceBreathV17');DEST='/Game/Monsters/IncineratorBossM66';V=DEST+'/FurnaceBreathV17';E=u.EditorAssetLibrary;P=u.AnimPoseExtensions
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before M66 furnace character save')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('M66 packages have unsaved changes')
bp=u.load_asset(DEST+'/BP_M66RigPreview');mesh=u.load_asset(V+'/SK_M66_Furnace_V17');clip=u.load_asset(V+'/A_M66_FurnaceBreath_V17');system=u.load_asset(V+'/NS_M66FurnaceBreath')
if not all((bp,mesh,clip,system)):raise RuntimeError('M66 furnace production asset missing')
cdo=u.get_default_object(bp.generated_class());manifest=json.loads((ROOT/'Records/animation_manifest.json').read_text());skin=json.loads((ROOT/'Records/skin_import.json').read_text())
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('M66 furnace animation finalization failed')
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
pose=P.get_anim_pose_at_time(clip,0.,options);root=P.get_ref_bone_pose(pose,'M66_Rig',u.AnimPoseSpaces.WORLD)
names=['Bone_001','Bone_006','Bone_010','Bone_015'];native=[manifest['source_reference_bones'][n] for n in names]
target=[P.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.WORLD).translation for n in names]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
basis=[sub(p,native[0]) for p in native[1:]];det=dot(basis[0],cross(basis[1],basis[2]));delta=sub(manifest['mouth_source_m'],native[0])
if abs(det)<1e-7:raise RuntimeError('M66 reference basis degenerate')
coeff=[dot(delta,cross(basis[1],basis[2]))/det,dot(basis[0],cross(delta,basis[2]))/det,dot(basis[0],cross(basis[1],delta))/det]
point=target[0]
for i,c in enumerate(coeff):point=point+(target[i+1]-target[0])*c
mouth_ref=P.get_ref_bone_pose(pose,'Bone_006',u.AnimPoseSpaces.WORLD);local=u.MathLibrary.inverse_transform_location(mouth_ref,point)
samples=[]
for frame in range(205):
    pose=P.get_anim_pose_at_time(clip,frame/60.,options);bone=P.get_bone_pose(pose,'Bone_006',u.AnimPoseSpaces.WORLD)
    samples.append(u.MathLibrary.transform_location(bone,local))
if not E.save_loaded_asset(clip,False):raise RuntimeError('M66 furnace finalized animation save failed')
settings={'visual_mesh':mesh,'breath_clip':clip,'breath_system':system,'breath_glow_material':u.load_asset(V+'/M_M66FurnaceGlow'),
    'breath_sound':u.load_asset(V+'/S_M66FurnaceRelease'),'breath_inhale_sound':u.load_asset(V+'/S_M66FurnaceInhale'),
    'breath_mouth_offset':local,'breath_reference_root':root,'breath_mouth_samples':samples,'breath_mouth_morph':skin['morph_name'],
    'breath_damage':25.,'breath_range':900.,'breath_minimum_range':400.,'breath_arc_degrees':35.,'breath_cooldown':12.}
for name,value in settings.items():
    if value is None:raise RuntimeError('M66 furnace setting asset missing '+name)
    cdo.set_editor_property(name,value)
component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh);component.set_physics_asset(cdo.get_editor_property('reaction_physics'),True);component.set_anim_instance_class(u.M66AnimInstance.static_class())
E.set_metadata_tag(bp,'M66.FurnaceBreath','V17: 0.95 s aim lock, 1.2-2.4 s six authoritative 25-fire pulses, .4 s hold and .6 s recovery; 9 m 35 degree fan')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 furnace character save failed')
report={'complete':True,'saved':[bp.get_path_name(),clip.get_path_name()],'mesh':mesh.get_path_name(),'morph':skin['morph_name'],'system':system.get_path_name(),
    'mouth_samples':len(samples),'range_cm':900,'arc_degrees':35,'damage_per_tick':25,'ticks':6,'cooldown_seconds':12,'duration_seconds':clip.get_play_length(),
    'sweep_preserved':cdo.get_editor_property('sweep_clip').get_path_name(),'slam_preserved':cdo.get_editor_property('slam_clip').get_path_name(),
    'back_smoke_enabled':cdo.get_editor_property('enable_back_smoke'),'server_authoritative':True,'runtime_tested':False,'multiplayer_tested':False,'rendered':False,'auditioned':False}
(ROOT/'Records/character_install.json').write_text(json.dumps(report,indent=2));print('M66_FURNACE_V17_SAVED '+json.dumps(report))
