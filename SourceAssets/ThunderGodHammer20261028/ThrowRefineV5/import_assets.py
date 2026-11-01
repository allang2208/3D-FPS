"""Replace only the two active throw clips; no mesh, gameplay or recall edits."""
import unreal as u,json,shutil,hashlib,datetime,math
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/ThunderGodHammer20261028/ThunderThrowV1'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
motion=json.loads((P/'motion.json').read_text(encoding='utf-8'))
receipt={'complete':False,'saved':[],'runtime_tested':False,'preview_rendered':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
record();backup=P/('BeforeImport-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir()
arms=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
A=u.AssetToolsHelpers.get_asset_tools();old=[]
for name in motion['clips']:
    file=R/'Content/Weapons/ThunderGodHammer20261028/ThunderThrowV1'/(name+'.uasset')
    if file.exists():shutil.copy2(file,backup/file.name);old.append({'file':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=arms.get_editor_property('skeleton')
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',240)
    t=u.AssetImportTask();t.filename=str(P/'Export'/(name+'.fbx'));t.destination_path=D;t.destination_name=name;t.automated=True;t.save=False;t.replace_existing=True;t.replace_existing_settings=True;t.options=opt
    A.import_asset_tasks([t]);clip=u.load_asset(D+'/'+name)
    if not clip:raise RuntimeError('Import failed '+name)
    clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    clip.set_editor_property('rate_scale',1.)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize failed '+name)
    u.EditorAssetLibrary.set_metadata_tag(clip,'ThunderThrowRevision','ThrowRefineV5: overhand grasp, continuous elbow branch, relaxed release wrists, V9 twist 100/50')
    if not u.EditorLoadingAndSavingUtils.save_packages([clip.get_outermost()],False):raise RuntimeError('Save failed '+name)
    receipt['saved'].append(clip.get_path_name());record()
(backup/'manifest.json').write_text(json.dumps(old,indent=2),encoding='utf-8')
# User-requested throw diagnosis: compare native source/compressed bones at
# the regrasp, swing, release and follow-through, without running gameplay.
native={};bones=['WPN_root']+[stem+'_'+s for s in ('l','r') for stem in ('upperarm','lowerarm','lowerarm_twist_01','lowerarm_twist_02','hand')]
for name in motion['clips']:
    clip=u.load_asset(D+'/'+name)
    times=[0,.18,.40,.60,.80,1.04,1.3,2.] if 'Charge' in name else [0,.06,.10,.16,.20,.24,.30,.36,.50,.70,.86]
    drift=0.;angle=0.;min_lengths={};max_lengths={}
    for time in times:
        samples=[]
        for mode in (u.AnimDataEvalType.SOURCE,u.AnimDataEvalType.COMPRESSED):
            opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=mode;opt.optional_skeletal_mesh=arms
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(time,clip.get_play_length()),opt)
            samples.append({b:u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD) for b in bones})
        for b in bones:
            a,c=samples[0][b],samples[1][b]
            drift=max(drift,math.dist([a.translation.x,a.translation.y,a.translation.z],[c.translation.x,c.translation.y,c.translation.z]))
            qa,qc=a.rotation,c.rotation
            dot=abs(qa.x*qc.x+qa.y*qc.y+qa.z*qc.z+qa.w*qc.w)
            angle=max(angle,math.degrees(2*math.acos(min(1.,dot))))
        for side in ('l','r'):
            for first,last in [('upperarm','lowerarm'),('lowerarm','hand')]:
                a=samples[1][first+'_'+side].translation;c=samples[1][last+'_'+side].translation
                length=math.dist([a.x,a.y,a.z],[c.x,c.y,c.z]);key=first+'_'+side
                min_lengths[key]=min(length,min_lengths.get(key,length));max_lengths[key]=max(length,max_lengths.get(key,length))
    native[name]={'times_seconds':times,'same_skeleton':clip.get_editor_property('skeleton')==arms.get_editor_property('skeleton'),
                  'length_seconds':clip.get_play_length(),'compression_position_error_cm':drift,'compression_rotation_error_deg':angle,
                  'bone_length_range_cm':{k:max_lengths[k]-v for k,v in min_lengths.items()}}
(P/'native-diagnosis.json').write_text(json.dumps(native,indent=2),encoding='utf-8')
receipt.update(complete=True,backup=str(backup),weapon_track='Existing authored WPN_root retained; launch header unchanged',runtime_paths='Existing Charge and Throw references reused');record()
print('THUNDER_THROW_REFINE_V5_IMPORTED',flush=True)
