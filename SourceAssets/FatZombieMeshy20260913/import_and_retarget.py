"""Import only FatZombie assets, author native IK rigs, and bake source motions."""
import unreal as u, json
from pathlib import Path

ROOT=Path(__file__).parent
DEST='/Game/Monsters/FatZombieMeshy'
at=u.AssetToolsHelpers.get_asset_tools(); lib=u.EditorAssetLibrary
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')

def save(a): lib.save_loaded_asset(a,False)
def create(name,folder,cls,factory):
    return u.load_asset(folder+'/'+name) or at.create_asset(name,folder,cls,factory)
def imp(file,name,folder,opts=None):
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=folder;t.destination_name=name
    t.automated=True;t.save=True;t.replace_existing=True
    if opts:t.options=opts
    at.import_asset_tasks([t])
    asset=u.load_asset(folder+'/'+name)
    if asset is None:raise RuntimeError('Import failed: '+str(t.imported_object_paths))
    return asset

def mesh(file,name,folder):
    o=u.FbxImportUI();o.automated_import_should_detect_type=False
    o.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    o.import_as_skeletal=True;o.import_mesh=True;o.import_animations=False
    o.import_materials=False;o.import_textures=False;o.create_physics_asset=True
    o.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    o.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
    o.skeletal_mesh_import_data.set_editor_property('convert_scene_unit',True)
    result=imp(file,name,folder,o)
    save(result.skeleton)
    if result.physics_asset:save(result.physics_asset)
    save(result)
    return result

target=mesh(ROOT/'prepared/SK_FatZombie_Meshy.fbx','SK_FatZombie_Meshy',DEST)
source=mesh(ROOT/'prepared/SK_M2M_Source.fbx','SK_M2M_Source',DEST+'/Sources')
clips=[]
for role in ['Idle','Walk','Attack','Death']:
    o=u.FbxImportUI();o.automated_import_should_detect_type=False
    o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;o.skeleton=source.skeleton
    o.import_mesh=False;o.import_animations=True;o.import_materials=False;o.import_textures=False
    o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    o.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    o.anim_sequence_import_data.set_editor_property('convert_scene_unit',True)
    clips.append(imp(ROOT/('prepared/A_M2M_'+role+'.fbx'),'A_M2M_'+role,DEST+'/Sources',o))

# Use the source PBR maps; tangent normals in the Meshy/Blender input are OpenGL.
mel=u.MaterialEditingLibrary
mat=create('M_FatZombie_Meshy',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
mat.set_editor_property('used_with_skeletal_mesh',True)
mel.delete_all_material_expressions(mat)
texbase=ROOT/'sources/meshy'
maps=[('BaseColor','_texture_0.png',u.MaterialProperty.MP_BASE_COLOR),
      ('Normal','_texture_0_normal.png',u.MaterialProperty.MP_NORMAL),
      ('Roughness','_texture_0_roughness.png',u.MaterialProperty.MP_ROUGHNESS),
      ('Metallic','_texture_0_metallic.png',u.MaterialProperty.MP_METALLIC)]
for index,(role,suffix,prop) in enumerate(maps):
    tex=imp(next(texbase.glob('*'+suffix)),'T_FatZombie_'+role,DEST+'/Textures')
    tex.set_editor_property('srgb',role=='BaseColor')
    if role=='Normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel',True)
    elif role in ['Roughness','Metallic']:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(tex)
    node=mel.create_material_expression(mat,u.MaterialExpressionTextureSample,-450,index*230)
    node.texture=tex
    node.sampler_type=(u.MaterialSamplerType.SAMPLERTYPE_NORMAL if role=='Normal' else
                       u.MaterialSamplerType.SAMPLERTYPE_COLOR if role=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    mel.connect_material_property(node,'R' if role in ['Roughness','Metallic'] else 'RGB',prop)
mel.recompile_material(mat);save(mat)
slots=target.materials
for i,slot in enumerate(slots):slot.material_interface=mat;slots[i]=slot
target.set_editor_property('materials',slots);save(target)

src_chains={'Spine':('spine_01','spine_03'),'Neck':('neck_01','neck_01'),'Head':('head','head'),
    'ClavicleLeft':('clavicle_l','clavicle_l'),'ClavicleRight':('clavicle_r','clavicle_r'),
    'ArmLeft':('upperarm_l','hand_l'),'ArmRight':('upperarm_r','hand_r'),
    'LegLeft':('thigh_l','foot_l'),'LegRight':('thigh_r','foot_r'),
    'ToeLeft':('ball_l','ball_l'),'ToeRight':('ball_r','ball_r')}
dst_chains={'Spine':('Spine02','Spine'),'Neck':('neck','neck'),'Head':('Head','Head'),
    'ClavicleLeft':('LeftShoulder','LeftShoulder'),'ClavicleRight':('RightShoulder','RightShoulder'),
    'ArmLeft':('LeftArm','LeftHand'),'ArmRight':('RightArm','RightHand'),
    'LegLeft':('LeftUpLeg','LeftFoot'),'LegRight':('RightUpLeg','RightFoot'),
    'ToeLeft':('LeftToeBase','LeftToeBase'),'ToeRight':('RightToeBase','RightToeBase')}
def ik(name,skel,pelvis,chains):
    asset=create(name,DEST+'/Rig',u.IKRigDefinition,u.IKRigDefinitionFactory())
    ctl=u.IKRigController.get_controller(asset);ctl.set_skeletal_mesh(skel);ctl.set_retarget_root(pelvis)
    existing={str(c.chain_name) for c in ctl.get_retarget_chains()}
    for chain,(start,end) in chains.items():
        if chain not in existing:ctl.add_retarget_chain(chain,start,end,'')
    save(asset);return asset
src=ik('IK_M2M_Source',source,'pelvis',src_chains)
dst=ik('IK_FatZombie_Meshy',target,'Hips',dst_chains)
rtg=create('RTG_M2M_FatZombie',DEST+'/Rig',u.IKRetargeter,u.IKRetargetFactory())
ctl=u.IKRetargeterController.get_controller(rtg)
ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,src);ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET,dst)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source);ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if ctl.get_num_retarget_ops()==0:ctl.add_default_ops()
ctl.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=ctl.create_retarget_pose('Meshy_Aligned',u.RetargetSourceOrTarget.TARGET)
ctl.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET)
ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(rtg)

params=u.IKRetargetBatchOperationInputs()
params.assets_to_retarget=[lib.find_asset_data(a.get_path_name()) for a in clips]
params.source_mesh=source;params.target_mesh=target;params.ik_retarget_asset=rtg
params.search='A_M2M_';params.replace='A_FatZombie_Raw_';params.target_path=DEST+'/RetargetedRaw'
params.include_referenced_assets=False;params.overwrite_existing_files=True
out=u.IKRetargetBatchOperation.run_batch_retarget(params)
folder=ROOT/'native_retarget';folder.mkdir(exist_ok=True)
report={}
for data in out:
    a=data.get_asset()
    if not isinstance(a,u.AnimSequence):continue
    a.set_preview_skeletal_mesh(target);a.set_editor_property('enable_root_motion',False);save(a)
    task=u.AssetExportTask();task.object=a;task.filename=str(folder/(a.get_name()+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.AnimSequenceExporterFBX();opts=u.FbxExportOption()
    opts.set_editor_property('export_preview_mesh',False);task.options=opts
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Could not export '+a.get_name())
    report[a.get_name()]={'asset':a.get_path_name(),'seconds':a.get_play_length(),'fbx':task.filename}
(ROOT/'native_retarget.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('FAT_ZOMBIE_NATIVE_RETARGET_COMPLETE '+json.dumps(report))
if (ROOT/'animation_contract.json').is_file():
    final_script=ROOT/'import_final.py'
    exec(compile(final_script.read_text(encoding='utf-8'),str(final_script),'exec'),
         {'__file__':str(final_script),'__name__':'__main__'})
