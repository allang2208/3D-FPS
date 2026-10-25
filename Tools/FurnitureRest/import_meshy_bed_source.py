"""Import licensed source and retarget both bed takes into isolated Jason assets."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/FurnitureRest20261022/MeshySitLieBed37120261024'
DEST='/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/MeshySource20261024'
E=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
def save(a):
    if isinstance(a,u.AnimSequence) and not u.WeaponAnimationAuthoring.finalize_authored_animation(a):raise RuntimeError('Compile '+a.get_path_name())
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())

if E.does_directory_exist(DEST):raise RuntimeError('Preserve existing source packages: '+DEST)
options=u.FbxImportUI();options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=True
options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
options.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
task=u.AssetImportTask();task.filename=str(OUT/'Meshy_Bed_Source.fbx');task.destination_path=DEST+'/Donor'
task.destination_name='SK_Meshy_Bed_Source';task.automated=True;task.replace_existing=False;task.save=True
task.options=options;task.factory=u.FbxFactory();assets.import_asset_tasks([task])
imported=[u.load_asset(p) for p in E.list_assets(DEST+'/Donor',True,False)]
source=next(a for a in imported if isinstance(a,u.SkeletalMesh))
clips=[a for a in imported if isinstance(a,u.AnimSequence)]
for a in imported:save(a)
print('MESHY_UE_SOURCE',source.get_path_name(),[a.get_name() for a in clips],flush=True)
body=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
target=u.load_asset(body['body_mesh'])

def rig(name,mesh,target_rig):
    obj=assets.create_asset(name,DEST+'/Rig',u.IKRigDefinition,u.IKRigDefinitionFactory())
    c=u.IKRigController.get_controller(obj);c.set_skeletal_mesh(mesh);c.set_retarget_root('pelvis')
    chains={'Spine':('spine_01','spine_05' if target_rig else 'spine_03'),
            'Neck':('neck_01','neck_02' if target_rig else 'neck_01'),'Head':('head','head')}
    for side in ('l','r'):
        for label,start,end in [('Clavicle','clavicle','clavicle'),('Arm','upperarm','hand'),('Leg','thigh','foot'),('Toe','ball','ball')]:
            chains[label+'_'+side]=(start+'_'+side,end+'_'+side)
    for label,(start,end) in chains.items():c.add_retarget_chain(label,start,end,'')
    save(obj);return obj

source_rig=rig('IK_Meshy_Bed',source,False);target_rig=rig('IK_Jason_Bed',target,True)
rtg=assets.create_asset('RTG_Meshy_Jason_Bed',DEST+'/Rig',u.IKRetargeter,u.IKRetargetFactory())
c=u.IKRetargeterController.get_controller(rtg)
c.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,source_rig);c.set_ik_rig(u.RetargetSourceOrTarget.TARGET,target_rig)
c.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source);c.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
c.add_default_ops();c.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=c.create_retarget_pose('JasonAligned',u.RetargetSourceOrTarget.TARGET);c.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET)
c.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET);save(rtg)
inputs=u.IKRetargetBatchOperationInputs();inputs.assets_to_retarget=[E.find_asset_data(a.get_path_name()) for a in clips]
inputs.source_mesh=source;inputs.target_mesh=target;inputs.ik_retarget_asset=rtg;inputs.prefix='J_';inputs.target_path=DEST+'/Retargeted'
inputs.include_referenced_assets=False;inputs.overwrite_existing_files=False
outputs=u.IKRetargetBatchOperation.run_batch_retarget(inputs)
results=[]
for entry in outputs:
    clip=entry.get_asset()
    if not isinstance(clip,u.AnimSequence):continue
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE);save(clip)
    results.append({'name':clip.get_name(),'path':clip.get_path_name(),'duration':clip.get_play_length()})
(OUT/'source_assets_saved.json').write_text(json.dumps({'source_mesh':source.get_path_name(),'target_mesh':target.get_path_name(),
    'source_clips':[a.get_path_name() for a in clips],'retargeter':rtg.get_path_name(),'clips':results,'runtime_published':False},indent=2))

seed=json.loads((ROOT/'SourceAssets/FurnitureRest20261022/ChairReuse20261024/authored.json').read_text())
result={k:seed[k] for k in ('mesh','skeleton','names','parents','reference')};result['clips']={}
def pack(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=target;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
for row in results:
    clip=u.load_asset(row['path']);duration=row['duration'];count=round(duration*30)+1;frames=[]
    for i in range(count):
        p=u.AnimPoseExtensions.get_anim_pose_at_time(clip,duration*i/(count-1),opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.LOCAL)) for n in result['names']])
    result['clips'][row['name']]={'duration':duration,'rate':30,'frames':frames,'asset':row['path']}
(OUT/'retargeted.json').write_text(json.dumps(result,separators=(',',':')))
print('MESHY_BED_RETARGETED',results,flush=True)
