"""Import the exclusive Aurora riser, its enamel finish and workbench icon into an isolated UE host."""
import json
import os
from pathlib import Path
import unreal as u

src=Path(__file__).resolve().parent
batch=Path(os.environ['AURORA_BATCH'])
family='/Game/Weapons/FrontierCompoundBow'
folder=family+'/AuroraFrameR1'
tools=u.AssetToolsHelpers.get_asset_tools()
edit=u.MaterialEditingLibrary
saved={}
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):
        raise RuntimeError('Could not save '+obj.get_path_name())
    saved[obj.get_name()]=obj.get_path_name()
def ingest(path,dest,options=None):
    task=u.AssetImportTask()
    task.filename=str(path);task.destination_path=dest;task.destination_name=path.stem
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True
    if options:task.options=options
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('Import produced no package: '+str(path))
    return u.load_asset(dest+'/'+path.stem)

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
textures={}
for key in ('Color','ORM','Normal','Glow'):
    tex=ingest(src/'Textures'/('T_Aurora_'+key+'.png'),folder+'/Textures')
    tex.srgb=key in ('Color','Glow')
    if key=='ORM':tex.compression_settings=u.TextureCompressionSettings.TC_MASKS;tex.compression_no_alpha=False
    if key=='Normal':tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP
    textures[key]=tex
    save(tex)
name='M_Aurora_Frame'
mat=u.load_asset(folder+'/'+name) if u.EditorAssetLibrary.does_asset_exist(folder+'/'+name) else tools.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
edit.delete_all_material_expressions(mat)
mat.set_editor_property('used_with_skeletal_mesh',True)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLEAR_COAT)
mat.set_editor_property('use_material_attributes',True)
attrs=edit.create_material_expression(mat,u.MaterialExpressionMakeMaterialAttributes,0,0)
pins={str(n).lower().replace(' ','').replace('_',''):str(n) for n in edit.get_material_expression_input_names(attrs)}
def wire(node,pin,name):
    if not edit.connect_material_expressions(node,pin,attrs,pins[name]):
        raise RuntimeError('Material attribute '+name)
for i,(key,sampler,channels) in enumerate([
    ('Color',u.MaterialSamplerType.SAMPLERTYPE_COLOR,{'RGB':'basecolor'}),
    ('ORM',u.MaterialSamplerType.SAMPLERTYPE_MASKS,{'R':'ambientocclusion','G':'roughness','B':'metallic','A':'clearcoat'}),
    ('Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL,{'RGB':'normal'}),
    ('Glow',u.MaterialSamplerType.SAMPLERTYPE_COLOR,{'RGB':'emissivecolor'})]):
    node=edit.create_material_expression(mat,u.MaterialExpressionTextureSample,-510,i*210)
    node.texture=textures[key];node.sampler_type=sampler
    for channel,pin in channels.items():wire(node,channel,pin)
clear=edit.create_material_expression(mat,u.MaterialExpressionConstant,-250,820)
clear.r=.19
wire(clear,'','clearcoatroughness')
if not edit.connect_material_property(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):raise RuntimeError('Material output')
edit.recompile_material(mat)
save(mat)
skeleton=u.load_asset(family+'/RigContactR2/SK_Frontier_Assembly_Skeleton')
if not skeleton:raise RuntimeError('Missing Frontier skeleton')
opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opts.import_as_skeletal=True;opts.import_mesh=True;opts.import_animations=False
opts.import_materials=False;opts.import_textures=False;opts.create_physics_asset=False
opts.skeleton=skeleton
opts.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
opts.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
opts.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
mesh=ingest(src/'Export/SK_Frontier_Aurora.fbx',folder,opts)
materials={'M_Aurora_Frame':mat, 'M_Frontier_Surface':u.load_asset(family+'/M_Frontier_Surface'),
           'M_Frontier_Cord':u.load_asset(family+'/M_Frontier_Cord')}
slots=list(mesh.materials)
if mesh.skeleton!=skeleton or set(str(s.material_slot_name) for s in slots)!=materials.keys() or not all(materials.values()):
    raise RuntimeError('FBX skeleton or slot mismatch: '+str([str(s.material_slot_name) for s in slots]))
for slot in slots:slot.material_interface=materials[str(slot.material_slot_name)]
mesh.materials=slots
skins=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
if not skins.regenerate_lod(mesh,3,False,False):raise RuntimeError('Could not build Aurora LODs')
save(mesh)
icon=ingest(src/'Export/bow_frontier_compound_riser_frontier_aurora.png','/Game/ColdSteelData/AttachmentIcons20260913/FramedBows')
icon.lod_group=u.TextureGroup.TEXTUREGROUP_UI;icon.srgb=True
icon.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
icon.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
save(icon)
(batch/'imported.json').write_text(json.dumps({'packages':saved,'skeleton':skeleton.get_path_name(),'lods':skins.get_lod_count(mesh),
    'slots':{k:v.get_path_name() for k,v in materials.items()}},indent=2),encoding='utf8')
