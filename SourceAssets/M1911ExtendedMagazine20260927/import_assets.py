"""Save this task's new 1911 mesh, steel finish, rain binding and UI textures."""
import ast,json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;PROJECT=O.parents[1]
D='/Game/Weapons/M1911/ExtendedMagazine20260927'
ICONS=D+'/Icons'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
auth=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
icons=json.loads((O/'icons.json').read_text(encoding='utf-8'))
targets={D+'/SM_M1911_ext_mag',D+'/Materials/M_M1911_ExtMag_Wall',D+'/DA_M1911_ExtMagWetMaterials'}
targets.update(D+'/Textures/'+Path(file).stem for file in auth['textures'].values())
targets.update(ICONS+'/T_'+key for key in icons)
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty&targets:raise RuntimeError('Unsaved M1911 target packages; preserve edits: '+str(sorted(dirty&targets)))
receipt={'saved':[],'textures':{},'icons':{},'game_tested':False}
def record(): (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name());record()

textures={}
for kind,file in auth['textures'].items():
    task=u.AssetImportTask();task.filename=file;task.destination_path=D+'/Textures';task.destination_name=Path(file).stem
    task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);tex=u.load_asset(task.destination_path+'/'+task.destination_name)
    if not tex:raise RuntimeError('Texture import failed '+file)
    tex.srgb=kind=='BaseColor'
    tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_DEFAULT
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON
    if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
    save(tex);textures[kind]=tex;receipt['textures'][kind]=tex.get_path_name()

# Reuse the existing weather graph construction helpers, without executing
# unrelated weather authoring or modifying a shared material/library package.
tree=ast.parse((PROJECT/'Tools/Weather/build_natural_weather.py').read_text(encoding='utf-8'))
names={'node','wire','prop','scalar','constant','vector','custom'};helpers={'unreal':u,'LIB':L}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'weather_graph_helpers','exec'),helpers)
node=helpers['node'];custom=helpers['custom'];prop=helpers['prop'];scalar=helpers['scalar']
path=D+'/Materials/M_M1911_ExtMag_Wall'
mat=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset('M_M1911_ExtMag_Wall',D+'/Materials',u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(mat);samples={}
for kind,tex in textures.items():
    sample=node(mat,u.MaterialExpressionTextureSample);sample.texture=tex
    sample.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR
    samples[kind]=sample
wet=scalar(mat,'WeaponWetness',0);uv=node(mat,u.MaterialExpressionTextureCoordinate)
beads=custom(mat,(PROJECT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(),dict(UV=uv,Wet=wet),4,'M1911 extended magazine rain')
prop(custom(mat,'return Base*(1-Data.a*.07);',dict(Base=samples['BaseColor'],Data=beads),3),'BASE_COLOR')
prop(custom(mat,'return lerp(lerp(ORM.g,max(.085,ORM.g*.70),Data.a),.065,Data.b*.8);',dict(ORM=samples['ORM'],Data=beads),1),'ROUGHNESS')
prop(custom(mat,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',dict(Base=samples['Normal'],Data=beads),3),'NORMAL')
L.connect_material_property(samples['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
L.connect_material_property(samples['ORM'],'B',u.MaterialProperty.MP_METALLIC)
E.set_metadata_tag(mat,'Source','Accepted M1911 magazine procedural steel baked onto the new lower band; original upper atlas unchanged')
L.recompile_material(mat);save(mat)

host=u.load_asset('/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny')
bindings={str(s.material_slot_name):s.material_interface for s in host.materials}
bindings['M_M1911_ExtMag_Wall']=mat
flag='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True
    opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    opt.override_full_name=True;opt.set_editor_property('reset_to_fbx_on_material_conflict',True)
    data=opt.static_mesh_import_data;data.combine_meshes=False;data.import_mesh_lods=True
    data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=str(O/'Exports/SM_M1911_ext_mag.fbx');task.destination_path=D
    task.destination_name='SM_M1911_ext_mag';task.options=opt;task.factory=u.FbxFactory()
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    if E.does_asset_exist(D+'/SM_M1911_ext_mag'):
        previous=u.load_asset(D+'/SM_M1911_ext_mag').get_editor_property('asset_import_data')
        previous.set_editor_property('import_mesh_lods',True);previous.set_editor_property('combine_meshes',False)
    A.import_asset_tasks([task]);mesh=u.load_asset(D+'/SM_M1911_ext_mag')
    if not mesh:raise RuntimeError('M1911 extended magazine import failed')
    slots=list(mesh.static_materials)
    for i,slot in enumerate(slots):slot.material_interface=bindings[str(slot.material_slot_name)];slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    E.set_metadata_tag(mesh,'M1911MagazineSource',str(O/'M1911_ExtendedMagazine_Editable.blend'))
    E.set_metadata_tag(mesh,'M1911MagazineFrame','Original 1911 skeletal mesh space; inverse WPN_SOCKET_Magazine reference chain; no guessed seat offset')
    E.set_metadata_tag(mesh,'SourceAttribution',auth['provenance'])
    save(mesh);receipt['mesh']={'asset':mesh.get_path_name(),'lods':mesh.get_num_lods(),
        'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials}}
    record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old))

path=D+'/DA_M1911_ExtMagWetMaterials'
if E.does_asset_exist(path):library=u.load_asset(path)
else:
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeatherPresentationAssets)
    library=A.create_asset('DA_M1911_ExtMagWetMaterials',D,u.WeatherPresentationAssets,factory)
library.set_editor_property('wet_materials',{mat.get_path_name():mat});save(library)
receipt['wet_library']=library.get_path_name()
for key,entry in icons.items():
    task=u.AssetImportTask();task.filename=entry['output'];task.destination_path=ICONS;task.destination_name='T_'+key
    task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);tex=u.load_asset(ICONS+'/T_'+key)
    if not tex:raise RuntimeError('Icon import failed '+key)
    tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    save(tex);receipt['icons'][key]=tex.get_path_name();record()
receipt['status']='imported_and_saved';record()
script=O/'update_catalog.py'
exec(compile(script.read_text(encoding='utf-8'),str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
receipt['catalog_published']=True;record()
print('M1911_EXTMAG_IMPORTED_AND_SAVED',flush=True)
