"""Import the heavy-clamp animation and bind contacts skinned by UE's imported bone poses."""
import ast,json,traceback,shutil
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/HeavyClampV01'
DEST='/Game/Monsters/HeQue';VERSION=DEST+'/HeavyClampV01'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();P=u.AnimPoseExtensions
report={'stage':'importing','saved':[],'runtime_tested':False,'multiplayer_tested':False,'visual_tested':False,'audio_auditioned':False}
RECEIPT=ROOT/'Records/ue-import.json'
helpers=ast.parse((PROJECT/'Tools/RootCrown/install.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in
    ('record','save','create','import_file','fbx','pose_at','align_root_units')],type_ignores=[]),'HeQue/heavy_clamp_import','exec'))

def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def values(v):return [v.x,v.y,v.z]

previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE before changing HeQue defaults')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved HeQue assets')
    # Preserve the exact existing Blueprint before this attack's defaults change.
    old=PROJECT/'Content/Monsters/HeQue/BP_HeQue.uasset';backup=ROOT/'Before/BP_HeQue.uasset'
    if old.exists() and not backup.exists():shutil.copy2(old,backup)
    mesh=u.load_asset(DEST+'/RigV01/SK_HeQue');bp=u.load_asset(DEST+'/BP_HeQue')
    if not mesh or not bp:raise RuntimeError('The delivered HeQue mesh/Blueprint is missing')
    motion=json.loads((ROOT/'Records/motion.json').read_text('utf8'))
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    options=fbx(True,mesh.skeleton);options.anim_sequence_import_data.set_editor_property('custom_sample_rate',motion['fps'])
    clip=import_file(ROOT/'Export/A_HeQue_HeavyClamp.fbx','A_HeQue_HeavyClamp',VERSION,options,u.FbxFactory())
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh)
    report['root_units']=align_root_units(clip,mesh)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Heavy clamp animation compilation did not finish')
    save(clip);save(mesh.skeleton)
    first=pose_at(clip,mesh,0.)
    # Infer Blender-to-imported-component-space conversion from four bind heads.
    # Bone-local axes may be changed by FBX; skin through UE's own bind/pose
    # transforms instead of assuming Blender bone-local axes survived export.
    names=list(motion['reference_heads']);src=[motion['reference_heads'][n] for n in names]
    dst=[values(P.get_ref_bone_pose(first,n,u.AnimPoseSpaces.WORLD).translation) for n in names]
    a,b,c=[sub(v,src[0]) for v in src[1:]];det=dot(a,cross(b,c))
    if abs(det)<1e-8:raise RuntimeError('Degenerate authoring bind basis')
    def imported(position):
        v=sub(position,src[0]);coeff=[dot(v,cross(b,c))/det,dot(v,cross(c,a))/det,dot(v,cross(a,b))/det]
        return u.Vector(*[dst[0][j]+sum(coeff[k]*(dst[k+1][j]-dst[0][j]) for k in range(3)) for j in range(3)])
    bindings=[]
    for sample in motion['surface_bindings']:
        position=imported(sample['position']);bound=[]
        for name,weight in sample['weights']:
            ref=P.get_ref_bone_pose(first,name,u.AnimPoseSpaces.WORLD)
            local=u.MathLibrary.inverse_transform_location(ref,position)
            bound.append((name,weight,local))
        bindings.append(bound)
    frames=[];rows=[]
    for source in motion['frames']:
        pose=pose_at(clip,mesh,source['time']);points=[]
        transforms={name:P.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD) for sample in bindings for name,_,_ in sample}
        for sample in bindings:
            point=[0.,0.,0.]
            for name,weight,local in sample:
                world=values(u.MathLibrary.transform_location(transforms[name],local))
                for j in range(3):point[j]+=world[j]*weight
            points.append(u.Vector(*point))
        frame=u.HeQueSweepFrame();frame.set_editor_property('time',source['time']);frame.set_editor_property('points',points)
        frames.append(frame);rows.append(dict(time=source['time'],points=[values(p) for p in points]))
    sound=import_file(ROOT/'Audio/S_HeQue_HeavyClamp.wav','S_HeQue_HeavyClamp',VERSION+'/Audio',factory=u.SoundFactory())
    sound.set_editor_property('volume',1.);save(sound)
    attenuation=create('SA_HeQue_HeavyClamp',VERSION+'/Audio',u.SoundAttenuation,u.SoundAttenuationFactory())
    settings=attenuation.get_editor_property('attenuation')
    settings.set_editor_property('attenuation_shape_extents',u.Vector(250,0,0))
    settings.set_editor_property('falloff_distance',1800.);settings.set_editor_property('spatialize',True)
    attenuation.set_editor_property('attenuation',settings);save(attenuation)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    for key,value in dict(clamp_clip=clip,clamp_frames=frames,clamp_damage=motion['damage'],clamp_cooldown=motion['cooldown'],
        clamp_trigger_range=motion['trigger_cm'],clamp_hit_radius=motion['hit_radius_cm'],clamp_sound=sound,clamp_attenuation=attenuation).items():
        cdo.set_editor_property(key,value)
    LIB.set_metadata_tag(bp,'HeQue.HeavyClamp','1.50s windup; 0.20s closure; contact ends 1.75; fixed facing and full recovery until 4.20s even on whiff')
    LIB.set_metadata_tag(bp,'HeQue.Stage','Heavy clamp, side crush, rift pressure, weighty locomotion, shared reactions and soft corpse')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    (ROOT/'Records/imported-contact-frames.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
    report.update(stage='heavy_clamp_saved',clip=clip.get_path_name(),blueprint=bp.get_path_name(),duration=clip.get_play_length(),
        contact_seconds=[motion['contact_start'],motion['contact_end']],contact_frames=len(frames),surface_samples=len(bindings),
        damage=motion['damage'],recovery_seconds=motion['recovery_seconds'],cooldown=motion['cooldown'],f6_label='合阙（重夹／碾扫／压鸣）',f6_id='HeQue',
        source_bind_heads=src,imported_bind_heads=dst)
    record();print('HEQUE_HEAVY_CLAMP_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
