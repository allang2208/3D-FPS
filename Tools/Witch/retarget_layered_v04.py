"""Author V04 native IK assets and export the unmodified retarget layer."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchMeshy20260919')
DEST='/Game/Monsters/WitchMeshy/LayeredV04'
lib=u.EditorAssetLibrary
at=u.AssetToolsHelpers.get_asset_tools()
source=u.load_asset('/Game/ZombieFemale/Asset/Meshes/ZombieFemale_NurseOutfit')
target=u.load_asset('/Game/Monsters/WitchMeshy/PreviousCloudGripV02/SK_Witch_Meshy')
if not source or not target: raise RuntimeError('Missing existing authoring inputs')
def create(name,cls,factory):
    return u.load_asset(DEST+'/Rig/'+name) or at.create_asset(name,DEST+'/Rig',cls,factory)
def save(obj):
    if not lib.save_loaded_asset(obj,False): raise RuntimeError('Save failed: '+obj.get_path_name())
src={'Spine':('spine_01','spine_05'),'Neck':('neck_01','neck_02'),'Head':('head','head')}
dst={'Spine':('Spine02','Spine'),'Neck':('neck','neck'),'Head':('Head','Head')}
for side,suffix in [('Left','l'),('Right','r')]:
    for chain,a,b,c,d in [('Clavicle','clavicle','clavicle','Shoulder','Shoulder'),('Arm','upperarm','hand','Arm','Hand'),('Leg','thigh','foot','UpLeg','Foot'),('Toe','ball','ball','ToeBase','ToeBase')]:
        src[chain+side]=(a+'_'+suffix,b+'_'+suffix)
        dst[chain+side]=(side+c,side+d)
def ik(name,mesh,root,chains):
    asset=create(name,u.IKRigDefinition,u.IKRigDefinitionFactory())
    ctl=u.IKRigController.get_controller(asset)
    ctl.set_skeletal_mesh(mesh);ctl.set_retarget_root(root)
    existing={str(c.chain_name) for c in ctl.get_retarget_chains()}
    for chain,(a,b) in chains.items():
        if chain not in existing:ctl.add_retarget_chain(chain,a,b,'')
    save(asset);return asset
s=ik('IK_Female_Source',source,'pelvis',src)
t=ik('IK_Witch_Original',target,'Hips',dst)
rtg=create('RTG_Female_Witch',u.IKRetargeter,u.IKRetargetFactory())
c=u.IKRetargeterController.get_controller(rtg)
c.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,s);c.set_ik_rig(u.RetargetSourceOrTarget.TARGET,t)
c.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source);c.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if c.get_num_retarget_ops()==0:c.add_default_ops()
c.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=c.create_retarget_pose('Female_Witch_Aligned',u.RetargetSourceOrTarget.TARGET)
c.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET)
c.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(rtg)
p=u.IKRetargetBatchOperationInputs()
p.assets_to_retarget=[lib.find_asset_data('/Game/ZombieFemale/Asset/Animations/ANMS_ZombieFemaleWalk01Forward')]
p.source_mesh=source;p.target_mesh=target;p.ik_retarget_asset=rtg
p.search='ANMS_ZombieFemale';p.replace='A_Witch_Raw_';p.target_path=DEST+'/RetargetedRaw'
p.include_referenced_assets=False;p.overwrite_existing_files=True
folder=ROOT/'Authoring/LayeredV04/RetargetedRaw';folder.mkdir(parents=True,exist_ok=True)
report=[]
for data in u.IKRetargetBatchOperation.run_batch_retarget(p):
    asset=data.get_asset()
    if not isinstance(asset,u.AnimSequence):continue
    save(asset)
    task=u.AssetExportTask();task.object=asset;task.filename=str(folder/(asset.get_name()+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.AnimSequenceExporterFBX();opt=u.FbxExportOption();opt.export_preview_mesh=False;task.options=opt
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Native retarget export failed')
    report.append({'asset':asset.get_path_name(),'seconds':asset.get_play_length(),'fbx':task.filename})
(folder/'native_retarget.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('WITCH_V04_NATIVE_RETARGET_SAVED '+json.dumps(report))
