"""Import the authored 715 and register its PBR/wet material and source clips."""
import unreal as u, json, ast
from pathlib import Path
O=Path(__file__).parent;ROOT=O.parents[1]
P='/Game/Weapons/DanWesson715/Integrated20260913'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
def save(asset):E.save_loaded_asset(asset,False);return asset
def task(source,dest,name=None,options=None):
    t=u.AssetImportTask();t.filename=str(source);t.destination_path=dest;t.destination_name=name or source.stem;t.automated=True;t.replace_existing=True;t.save=True
    if options:t.options=options
    A.import_asset_tasks([t]);return u.load_asset(dest+'/'+t.destination_name)
textures={}
for kind in ['BaseColor','Normal','ORM']:
    texture=task(O/f'Textures/T_DW715_{kind}.png',P+'/Textures')
    texture.srgb=kind=='BaseColor'
    texture.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_DEFAULT
    texture.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON
    if kind=='Normal':texture.flip_green_channel=True
    textures[kind]=save(texture)
def material(name):
    path=P+'/Materials/'+name
    m=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m);return m
def node(m,cls):return L.create_material_expression(m,cls)
def link(src,output,dest,input):L.connect_material_expressions(src,output,dest,input)
def property(src,out,name):L.connect_material_property(src,out,getattr(u.MaterialProperty,'MP_'+name))
surface=material('M_DW715_Surface');samples={}
for kind in textures:
    n=node(surface,u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name','DW715_'+kind);n.set_editor_property('texture',textures[kind])
    n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    samples[kind]=n
property(samples['BaseColor'],'RGB','BASE_COLOR');property(samples['Normal'],'RGB','NORMAL')
for channel,propname in [('R','AMBIENT_OCCLUSION'),('G','ROUGHNESS'),('B','METALLIC')]:property(samples['ORM'],channel,propname)
L.set_material_usage(surface,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
L.recompile_material(surface);save(surface)
loader=material('M_DW715_Loader')
color=node(loader,u.MaterialExpressionConstant3Vector);color.set_editor_property('constant',u.LinearColor(.024,.028,.033,1));property(color,'','BASE_COLOR')
rough=node(loader,u.MaterialExpressionConstant);rough.set_editor_property('r',.48);property(rough,'','ROUGHNESS')
L.set_material_usage(loader,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);L.recompile_material(loader);save(loader)
ref=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
bindings={str(s.material_slot_name):s.material_interface for s in ref.materials}
bindings.update({'M_DW715_Surface':surface,'M_DW715_Loader':loader})
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
if E.does_asset_exist(P+'/SK_DW715_Manny'):opt.skeleton=u.load_asset(P+'/SK_DW715_Manny').skeleton
opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
mesh=task(O/'SK_DW715_Manny.fbx',P,options=opt)
slots=mesh.materials
for i,slot in enumerate(slots):slot.material_interface=bindings[str(slot.material_slot_name)];slots[i]=slot
mesh.materials=slots;save(mesh)
clips={}
for source in sorted((O/'Animations').glob('*.fbx')):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    clip=task(source,P+'/Animations',options=opt)
    compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    if compression:clip.set_editor_property('bone_compression_settings',compression)
    save(clip);clips[source.stem]=clip.get_path_name()
for source in sorted((O/'Audio').glob('*.wav')):task(source,P+'/Audio')
# Use the project's water-bead material helpers without regenerating weather.
unreal=u;LIB=L;TOOLS=A;DEST=P+'/Materials';REPORT={'materials':[]}
tree=ast.parse((ROOT/'Tools/Weather/build_natural_weather.py').read_text(encoding='utf-8'))
helpers={'node','wire','prop','scalar','constant','vector','custom','save'}
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in helpers],type_ignores=[]),'<weather graph construction>','exec'))
wetpath=P+'/Materials/M_DW715_Wet'
wet=u.load_asset(wetpath) if E.does_asset_exist(wetpath) else E.duplicate_asset(surface.get_path_name(),wetpath)
if not E.get_metadata_tag(wet,'DW715WetGraph'):
    original={}
    for name in ['BASE_COLOR','ROUGHNESS','NORMAL']:
        propid=getattr(u.MaterialProperty,'MP_'+name);n=L.get_material_property_input_node(wet,propid)
        original[name]=(n,L.get_material_property_input_node_output_name(wet,propid))
    beads=custom(wet,(ROOT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(),dict(UV=node(wet,u.MaterialExpressionTextureCoordinate),Wet=scalar(wet,'WeaponWetness',0)),4,'WeatherBeads')
    prop(custom(wet,'return Base*(1-Data.a*.07);',dict(Base=original['BASE_COLOR'],Data=beads),3),'BASE_COLOR')
    prop(custom(wet,'return lerp(lerp(Base,max(.085,Base*.70),Data.a),.065,Data.b*.8);',dict(Base=original['ROUGHNESS'],Data=beads),1),'ROUGHNESS')
    prop(custom(wet,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',dict(Base=original['NORMAL'],Data=beads),3),'NORMAL')
    E.set_metadata_tag(wet,'DW715WetGraph','1');L.set_material_usage(wet,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);save(wet)
for path in ['/Game/Weather/RainVisibility/DA_WeatherPresentation','/Game/Weather/NaturalV2/DA_WeatherPresentation']:
    library=u.load_asset(path);mapping=dict(library.get_editor_property('wet_materials'));mapping[surface.get_path_name()]=wet;library.set_editor_property('wet_materials',mapping);save(library)
(O/'import.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'animations':clips,'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots},'status':'Imported; no game, render or listening tests performed'},indent=2))
u.log('DW715_IMPORT_COMPLETE')
