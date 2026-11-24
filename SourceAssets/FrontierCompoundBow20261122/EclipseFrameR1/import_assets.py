"""Import the Eclipse mesh, authored PBR finish and workbench card into the content host."""
from pathlib import Path
import json, os
import unreal as u
src=Path(__file__).resolve().parent
batch=Path(os.environ['ECLIPSE_BATCH'])
family='/Game/Weapons/FrontierCompoundBow'
folder=family+'/EclipseFrameR1'
tools=u.AssetToolsHelpers.get_asset_tools()
edit=u.MaterialEditingLibrary
packages={}
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Could not save '+asset.get_path_name())
    packages[asset.get_name()]=asset.get_path_name()
def ingest(path,destination,options=None):
    task=u.AssetImportTask()
    task.filename=str(path);task.destination_path=destination;task.destination_name=path.stem
    task.automated=True;task.replace_existing=True
    if options:task.options=options
    tools.import_asset_tasks([task])
    result=u.load_asset(destination+'/'+path.stem)
    if not result:raise RuntimeError('Import failed '+str(path))
    return result
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
textures={}
for key in ('Color','ORM','Normal'):
    t=ingest(src/'Textures'/f'T_Eclipse_{key}.png',folder+'/Textures')
    t.srgb=key=='Color'
    if key=='ORM':t.compression_settings=u.TextureCompressionSettings.TC_MASKS
    if key=='Normal':t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP
    save(t);textures[key]=t
name='M_Eclipse_Frame'
mat=u.load_asset(folder+'/'+name) if u.EditorAssetLibrary.does_asset_exist(folder+'/'+name) else tools.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
edit.delete_all_material_expressions(mat)
mat.set_editor_property('used_with_skeletal_mesh',True)
for idx,(key,pins,sampler) in enumerate([
        ('Color',{'RGB':u.MaterialProperty.MP_BASE_COLOR},u.MaterialSamplerType.SAMPLERTYPE_COLOR),
        ('ORM',{'R':u.MaterialProperty.MP_AMBIENT_OCCLUSION,'G':u.MaterialProperty.MP_ROUGHNESS,'B':u.MaterialProperty.MP_METALLIC},u.MaterialSamplerType.SAMPLERTYPE_MASKS),
        ('Normal',{'RGB':u.MaterialProperty.MP_NORMAL},u.MaterialSamplerType.SAMPLERTYPE_NORMAL)]):
    node=edit.create_material_expression(mat,u.MaterialExpressionTextureSample,-380,idx*210)
    node.texture=textures[key];node.sampler_type=sampler
    for channel,pin in pins.items():
        if not edit.connect_material_property(node,channel,pin):raise RuntimeError('Material input '+channel)
edit.recompile_material(mat);save(mat)
skeleton=u.load_asset(family+'/RigContactR2/SK_Frontier_Assembly_Skeleton')
if not skeleton:raise RuntimeError('Missing production skeleton')
opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opts.import_as_skeletal=True;opts.import_mesh=True;opts.import_materials=False
opts.import_textures=False;opts.import_animations=False;opts.create_physics_asset=False
opts.skeleton=skeleton
settings=opts.skeletal_mesh_import_data
settings.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
settings.set_editor_property('update_skeleton_reference_pose',False)
settings.set_editor_property('use_t0_as_ref_pose',False)
skin=ingest(src/'Export/SK_Frontier_Eclipse.fbx',folder,opts)
if skin.skeleton!=skeleton:raise RuntimeError('Unexpected skeleton')
mats={'M_Eclipse_Frame':mat,'M_Frontier_Surface':u.load_asset(family+'/M_Frontier_Surface'),'M_Frontier_Cord':u.load_asset(family+'/M_Frontier_Cord')}
slots=list(skin.materials)
for slot in slots:
    key=str(slot.material_slot_name)
    if not mats.get(key):raise RuntimeError('Unbound: '+key)
    slot.material_interface=mats[key]
skin.materials=slots
skins=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
if not skins.regenerate_lod(skin,3,False,False):raise RuntimeError('Failed to generate LODs')
save(skin)
icon=ingest(src/'Export/bow_frontier_compound_riser_frontier_eclipse.png','/Game/ColdSteelData/AttachmentIcons20260913/FramedBows')
icon.lod_group=u.TextureGroup.TEXTUREGROUP_UI;icon.srgb=True
icon.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
icon.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
save(icon)
(batch/'imported.json').write_text(json.dumps({'packages':packages,'skeleton':skeleton.get_path_name(),
    'slots':{str(slot.material_slot_name):slot.material_interface.get_path_name() for slot in slots}},indent=2),encoding='utf8')
