"""Bake the existing 59 world-body clips onto Jason's native MetaHuman skeleton."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonPlayer20261003')
exec(compile(Path('D:/FPS3D/FPSGAME/Tools/PlayerBody/extract_jason_regions.py').read_text(), 'extract_jason_regions.py', 'exec'))
DEST='/Game/Characters/JasonPlayer20261003'
lib=u.EditorAssetLibrary
at=u.AssetToolsHelpers.get_asset_tools()
cfg=json.loads((ROOT/'Before/Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
source=u.load_asset(cfg['body_mesh'])
target=u.load_asset('/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body')
if not source or not target:raise RuntimeError('Missing source or target mesh')

def save(asset):
    if not lib.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
def create(name,cls,factory):
    return u.load_asset(DEST+'/Rig/'+name) or at.create_asset(name,DEST+'/Rig',cls,factory)

chains={'Spine':('spine_01','spine_05'),'Neck':('neck_01','neck_02'),'Head':('head','head')}
for side in ('l','r'):
    for name,start,end in [('Clavicle','clavicle','clavicle'),('Arm','upperarm','hand'),('Leg','thigh','foot'),('Toe','ball','ball')]:
        chains[name+'_'+side]=(start+'_'+side,end+'_'+side)
    for digit in ('thumb','index','middle','ring','pinky'):
        chains[digit+'_'+side]=(digit+'_01_'+side,digit+'_03_'+side)
def make_ik(name,mesh):
    ik=create(name,u.IKRigDefinition,u.IKRigDefinitionFactory())
    ctl=u.IKRigController.get_controller(ik)
    ctl.set_skeletal_mesh(mesh);ctl.set_retarget_root('pelvis')
    names={str(c.chain_name) for c in ctl.get_retarget_chains()}
    for name,(start,end) in chains.items():
        if name not in names:ctl.add_retarget_chain(name,start,end,'')
    save(ik);return ik
src=make_ik('IK_Manny_Source',source)
dst=make_ik('IK_Jason_Target',target)
rtg=create('RTG_Manny_Jason',u.IKRetargeter,u.IKRetargetFactory())
ctl=u.IKRetargeterController.get_controller(rtg)
ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,src)
ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET,dst)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if ctl.get_num_retarget_ops()==0:ctl.add_default_ops()
ctl.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=ctl.create_retarget_pose('Jason_Aligned',u.RetargetSourceOrTarget.TARGET)
ctl.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET)
ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(rtg)
p=u.IKRetargetBatchOperationInputs()
p.assets_to_retarget=[lib.find_asset_data(path) for path in dict.fromkeys(cfg['clips'].values())]
p.source_mesh=source;p.target_mesh=target;p.ik_retarget_asset=rtg
p.prefix='J_';p.target_path=DEST+'/Animations';p.include_referenced_assets=False;p.overwrite_existing_files=True
outputs=u.IKRetargetBatchOperation.run_batch_retarget(p)
saved={}
for data in outputs:
    a=data.get_asset()
    if not isinstance(a,u.AnimSequence):continue
    a.set_preview_skeletal_mesh(target);a.set_editor_property('enable_root_motion',False)
    save(a);saved[a.get_name()]=a.get_path_name()
clips={}
for key,path in cfg['clips'].items():
    name='J_'+path.split('.')[-1]
    if name not in saved:raise RuntimeError('Retarget did not save '+name)
    clips[key]=saved[name]
(ROOT/'retargeted_clips.json').write_text(json.dumps(clips,indent=2),encoding='utf-8')
print('JASON_ANIMATIONS_SAVED '+str(len(clips)),flush=True)

# Region input for clothing fitting; no rendering or runtime probes.
for key in ('NativeSkin','Jason','ue_field_gloves_skin'):
    path=ROOT/(key+'.json');d=json.loads(path.read_text())
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(u.load_asset(d['source']),u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    mids=[]
    for i in range(len(d['triangles'])):
        result=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
        mids.append(int(result[0] if isinstance(result,tuple) else result))
    d['triangle_materials']=mids;path.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
print('JASON_REGION_INPUTS_SAVED',flush=True)
