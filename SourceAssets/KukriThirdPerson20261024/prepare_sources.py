"""Import local single-hand donors and retarget into new Kukri-only packages."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME'); OUT=ROOT/'SourceAssets/KukriThirdPerson20261024'
DEST='/Game/Characters/JasonPlayer20261003/Kukri20261024'
lib=u.EditorAssetLibrary; assets=u.AssetToolsHelpers.get_asset_tools()
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
target=u.load_asset(cfg['body_mesh'])
free=json.loads((ROOT/'SourceAssets/ThirdPersonSwordFree20261005/imported-sources.json').read_text())

def save(a):
    if not lib.save_loaded_asset(a,False): raise RuntimeError('Save failed: '+a.get_path_name())

kevin_path=DEST+'/Donors/SK_Kevin_Kukri'
if not lib.does_asset_exist(kevin_path):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False
    opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
    task=u.AssetImportTask();task.filename=str(ROOT/'SourceAssets/ThirdPersonSwordFree20261005/Kevin/Models/HumanM_Model.fbx')
    task.destination_path=DEST+'/Donors';task.destination_name='SK_Kevin_Kukri'
    task.automated=True;task.replace_existing=False;task.save=True;task.options=opt;task.factory=u.FbxFactory()
    assets.import_asset_tasks([task])
kevin=u.load_asset(kevin_path)
for name in ('CombatIdle1H01','Attack1H01_R'):
    path=DEST+'/Donors/A_Kevin_'+name
    if lib.does_asset_exist(path): continue
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_as_skeletal=False;opt.import_mesh=False;opt.import_animations=True
    opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
    opt.skeleton=kevin.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
    task=u.AssetImportTask()
    task.filename=str(ROOT/f'SourceAssets/ThirdPersonSwordFree20261005/Kevin/Animations/Male/Combat/1H/HumanM@{name}.fbx')
    task.destination_path=DEST+'/Donors';task.destination_name='A_Kevin_'+name
    task.automated=True;task.replace_existing=False;task.save=True;task.options=opt;task.factory=u.FbxFactory()
    assets.import_asset_tasks([task])
    clip=u.load_asset(path)
    if not isinstance(clip,u.AnimSequence): raise RuntimeError('Missing donor '+path)
    save(clip)

kayprefix='/Game/Characters/JasonPlayer20261003/SwordFullBody20261005/Donors/KayKit/'
ualprefix='/Game/Characters/JasonPlayer20261003/SwordDonorRepair20261006/Source/Donor/'
groups={
 'Kevin': dict(mesh=kevin_path,rtg='/Game/Characters/JasonPlayer20261003/SwordFullBody20261005/Rig/RTG_Kevin_Jason_Sword',
   clips={'Idle':DEST+'/Donors/A_Kevin_CombatIdle1H01','KevinCut':DEST+'/Donors/A_Kevin_Attack1H01_R'}),
 'KayKit': dict(mesh=free['KayKit']['mesh'],rtg='/Game/Characters/JasonPlayer20261003/SwordFullBody20261005/Rig/RTG_KayKit_Jason_Sword',
   clips={label:kayprefix+'SK_KayKit_Medium_Anim_Melee_1H_Attack_'+suffix for label,suffix in
     [('Slash1','Slice_Horizontal'),('Slash2','Slice_Diagonal'),('Thrust','Stab'),('Heavy','Chop'),('Dash','Jump_Chop')]}),
 'UAL2':dict(mesh=ualprefix+'SK_UAL2_Mannequin',rtg='/Game/Characters/JasonPlayer20261003/SwordDonorRepair20261006/Source/Rig/RTG_UAL2_Jason_Sword',
   clips={label:ualprefix+'A_UAL2_Armature_'+name for label,name in
     [('RegularC','Sword_Regular_C'),('HeavyCombo','Sword_Heavy_Combo'),('DashCut','Sword_Dash'),('Hook','Melee_Hook')]}),
}
selected={}
for group,data in groups.items():
    source=u.load_asset(data['mesh']);rtg=u.load_asset(data['rtg'])
    if not source or not rtg: raise RuntimeError('Missing rig '+group)
    pending=[p for p in data['clips'].values() if not lib.does_asset_exist(DEST+'/Retargeted/J_Kukri_'+p.split('/')[-1])]
    if pending:
        batch=u.IKRetargetBatchOperationInputs()
        batch.assets_to_retarget=[lib.find_asset_data(p) for p in pending]
        batch.source_mesh=source;batch.target_mesh=target;batch.ik_retarget_asset=rtg
        batch.prefix='J_Kukri_';batch.target_path=DEST+'/Retargeted'
        batch.include_referenced_assets=False;batch.overwrite_existing_files=False
        u.IKRetargetBatchOperation.run_batch_retarget(batch)
    for label,path in data['clips'].items():
        clip=u.load_asset(DEST+'/Retargeted/J_Kukri_'+path.split('/')[-1])
        if not isinstance(clip,u.AnimSequence): raise RuntimeError('Missing retarget '+label)
        clip.set_preview_skeletal_mesh(target);save(clip)
        selected[label]=(clip,path,group)

pommel=u.load_asset('/Game/Characters/JasonPlayer20261003/StaffPunch20261009/Donors/J_SK_KayKit_Medium_Anim_Melee_Unarmed_Attack_Punch_A')
if not isinstance(pommel,u.AnimSequence): raise RuntimeError('Missing local full-body punch donor')
selected['Pommel']=(pommel,kayprefix+'SK_KayKit_Medium_Anim_Melee_Unarmed_Attack_Punch_A','KayKit')

def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
ref=target.skeleton.get_reference_pose();names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(target)
parents=[names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names]
result=dict(mesh=target.get_path_name(),skeleton=target.skeleton.get_path_name(),names=names,parents=parents,
 reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],clips={})
options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=target;options.evaluation_type=u.AnimDataEvalType.SOURCE
summary={}
for label,(clip,source,group) in selected.items():
    length=clip.get_play_length();count=max(2,round(length*30)+1);frames=[];hands=[]
    for i in range(count):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,length*i/(count-1),options)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
        hands.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in ('hand_r','hand_l','pelvis','head')})
    result['clips'][label]=dict(asset=clip.get_path_name(),source=source,group=group,duration=length,rate=30,frames=frames,hands=hands)
    summary[label]=dict(duration=length,samples=[dict(time=round(length*j/8,3),right=hands[round((count-1)*j/8)]['hand_r'][:3],left=hands[round((count-1)*j/8)]['hand_l'][:3]) for j in range(9)])
    print('KUKRI_DONOR_READY '+label,flush=True)
(OUT/'retargeted-poses.json').write_text(json.dumps(result,separators=(',',':')))
(OUT/'source-motion-summary.json').write_text(json.dumps(summary,indent=2))
(OUT/'sources-ready.json').write_text(json.dumps(dict(complete=True,clips={k:v['asset'] for k,v in result['clips'].items()}),indent=2))
items=json.loads((ROOT/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
native=u.load_asset(items['ue_kukri']['viewmodel_mesh'])
hold=u.load_asset('/Game/Weapons/Kukri20261020/Animations/A_Kukri_Idle')
native_options=u.AnimPoseEvaluationOptions();native_options.optional_skeletal_mesh=native;native_options.evaluation_type=u.AnimDataEvalType.SOURCE
pose=u.AnimPoseExtensions.get_anim_pose_at_time(hold,0.,native_options)
native_names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)]
grip={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in native_names
      if n=='hand_r' or n=='WPN_root' or (n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky')))}
(OUT/'native-grip.json').write_text(json.dumps(dict(mesh=native.get_path_name(),hold=hold.get_path_name(),bones=grip),indent=2))
print('KUKRI_DONORS_COMPLETE',flush=True)
if (OUT/'selection.json').exists():
    # Keep the dependent author/save operations in this one asset batch.
    import subprocess
    subprocess.run([r'C:\Users\allan\AppData\Local\Programs\Python\Python311\python.exe',str(OUT/'author_actions.py')],check=True)
    exec(compile((OUT/'save_actions.py').read_text(),str(OUT/'save_actions.py'),'exec'),
         {'__name__':'__main__','__file__':str(OUT/'save_actions.py')})
