"""Editor/commandlet asset production. Runs under the existing batch mutex."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;ROOT='/Game/Weapons/G18/Drum50_20261003';BASE='/Game/Weapons/G18/Integrated20260929'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report={'complete':False,'saved':[],'runtime_tested':False}
def save(obj):
    if not E.save_loaded_asset(obj,only_if_is_dirty=False):raise RuntimeError('Save failed: '+obj.get_path_name())
    report['saved'].append(obj.get_path_name());(O/'import_receipt.json').write_text(json.dumps(report,indent=2))
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Asset missing: '+path)
    return obj
def imported(file,path,options=None):
    folder,name=path.rsplit('/',1);task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    A.import_asset_tasks([task]);return load(path)
textures={}
for channel in ('BaseColor','ORM','Normal_DirectX'):
    name='T_G18_Drum50_'+channel;tex=imported(O/'Textures'/(name+'.png'),ROOT+'/Textures/'+name)
    tex.srgb=channel=='BaseColor';tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal_DirectX' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if channel=='Normal_DirectX' else u.TextureGroup.TEXTUREGROUP_WEAPON
    if channel=='Normal_DirectX':tex.flip_green_channel=False
    save(tex);textures[channel]=tex
path=ROOT+'/Materials/M_G18_Drum50_PBR';mat=load(path) if E.does_asset_exist(path) else A.create_asset('M_G18_Drum50_PBR',ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(mat)
def node(cls):return L.create_material_expression(mat,cls,0,0)
def wire(a,output,b,input):L.connect_material_expressions(a,output,b,input)
samples={}
for channel,tex in textures.items():
    n=node(u.MaterialExpressionTextureSample);n.texture=tex;n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal_DirectX' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR;samples[channel]=n
wet=node(u.MaterialExpressionScalarParameter);wet.parameter_name='WeaponWetness';wet.default_value=0
def custom(code,connections,outtype):
    n=node(u.MaterialExpressionCustom);n.code=code;n.output_type=outtype;n.inputs=[u.CustomInput(input_name=k) for k in connections]
    for key,(src,pin) in connections.items():wire(src,pin,n,key)
    return n
base=custom('return Base*(1-0.07*saturate(Wet));',{'Base':(samples['BaseColor'],'RGB'),'Wet':(wet,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
rough=custom('return lerp(Rough,max(0.085,Rough*0.65),saturate(Wet));',{'Rough':(samples['ORM'],'G'),'Wet':(wet,'')},u.CustomMaterialOutputType.CMOT_FLOAT1)
for n,pin,prop in [(base,'',u.MaterialProperty.MP_BASE_COLOR),(rough,'',u.MaterialProperty.MP_ROUGHNESS),(samples['ORM'],'B',u.MaterialProperty.MP_METALLIC),(samples['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),(samples['Normal_DirectX'],'RGB',u.MaterialProperty.MP_NORMAL)]:L.connect_material_property(n,pin,prop)
L.recompile_material(mat);save(mat)
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.lod_number=3;opt.auto_compute_lod_distances=True
    d=opt.static_mesh_import_data;d.combine_meshes=False;d.import_mesh_lods=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.build_nanite=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=imported(O/'Exports/SM_G18_Drum50.fbx',ROOT+'/Meshes/SM_G18_Drum50',opt)
    materials={'M_G18_Drum50_PBR':mat,'M_G18_Magazine':load(BASE+'/Materials/M_G18_SourcePBR')}
    for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,materials[str(slot.material_slot_name)])
    E.set_metadata_tag(mesh,'Source','User drum reference; G18 factory upper interface; game visual model only')
    E.set_metadata_tag(mesh,'SourceSHA256',hashlib.sha256((O/'Exports/SM_G18_Drum50.fbx').read_bytes()).hexdigest());save(mesh)
    report['mesh']=mesh.get_path_name();extent=mesh.get_bounds().box_extent;report['bounds_half_extent_cm']=[extent.x,extent.y,extent.z]
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))
library=load(BASE+'/DA_G18_WetMaterials');wetmap=dict(library.get_editor_property('wet_materials'));wetmap[mat.get_path_name()]=mat;library.set_editor_property('wet_materials',wetmap);save(library)
iconfile=O/'Icons/ue_g18_magazine_g18_drum_50.png'
icon=imported(iconfile,'/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms/'+iconfile.stem)
icon.srgb=True;icon.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;icon.lod_group=u.TextureGroup.TEXTUREGROUP_UI;icon.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;save(icon)
report['complete']=True;(O/'import_receipt.json').write_text(json.dumps(report,indent=2));print('G18_DRUM50_ASSETS_SAVED',flush=True)
