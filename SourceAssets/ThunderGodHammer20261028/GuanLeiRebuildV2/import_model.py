"""Save only this rebuilt seat and its PBR assets through the current UE bridge."""
import unreal as u,json,re
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/ThunderGodHammer20261028/GuanLeiRebuildV2'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'complete':False,'saved':[],'runtime_tested':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not asset or not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+str(asset))
    receipt['saved'].append(asset.get_path_name());record();return asset
def imp(path,name,folder,options=None):
    t=u.AssetImportTask();t.filename=str(path);t.destination_name=name;t.destination_path=folder;t.automated=True;t.save=False;t.replace_existing=True;t.replace_existing_settings=True
    if options:t.options=options
    A.import_asset_tasks([t]);asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Import failed '+name)
    return asset
record();textures={}
for key in ['BaseColor','ORM','Normal','Emissive']:
    name='T_GuanLeiV2_'+key;tex=imp(P/'Textures'/(name+'.png'),name,D+'/Textures')
    tex.set_editor_property('srgb',key in ['BaseColor','Emissive']);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal' else u.TextureCompressionSettings.TC_MASKS if key=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
    if key=='Normal':tex.set_editor_property('flip_green_channel',True)
    textures[key]=save(tex)
mat=u.load_asset(D+'/M_GuanLeiSeatV2') or A.create_asset('M_GuanLeiSeatV2',D,u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(mat);mat.set_editor_property('used_with_nanite',True)
surface=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels);surface.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
nodes={}
for key,tex in textures.items():
    n=L.create_material_expression(mat,u.MaterialExpressionTextureSample);n.set_editor_property('texture',tex);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if key=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);nodes[key]=n
for key,channel,pin,prop in [('BaseColor','RGB','BaseColor',u.MaterialProperty.MP_BASE_COLOR),('ORM','G','Roughness',u.MaterialProperty.MP_ROUGHNESS),('ORM','B','Metallic',u.MaterialProperty.MP_METALLIC),('Normal','RGB','Normal',u.MaterialProperty.MP_NORMAL)]:
    if not L.connect_material_expressions(nodes[key],channel,surface,pin):raise RuntimeError('Pin '+pin)
    L.connect_material_property(nodes[key],channel,prop)
em=L.create_material_expression(mat,u.MaterialExpressionMultiply);em.set_editor_property('const_b',3.0);L.connect_material_expressions(nodes['Emissive'],'RGB',em,'A')
names={str(n).replace(' ','').lower():str(n) for n in L.get_material_expression_input_names(surface)}
if not L.connect_material_expressions(em,'',surface,names['emissivecolor']):raise RuntimeError('Emission input')
L.connect_material_property(em,'',u.MaterialProperty.MP_EMISSIVE_COLOR);L.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL)
L.layout_material_expressions(mat);errors=L.recompile_material(mat)
if errors:raise RuntimeError(str(errors))
save(mat)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
name='SM_ThunderHammer_GuanLeiSeatV2';mesh=imp(P/'Export'/(name+'.fbx'),name,D,opt)
materials={'M_GuanLeiSeatV2':mat,'M_ThunderGodHammerSurface':u.load_asset('/Game/Weapons/ThunderGodHammer20261028/Materials/M_ThunderGodHammerSurface')}
for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,materials[re.sub(r'(?:[._]\d{3})+$','',str(s.material_slot_name))])
n=mesh.get_editor_property('nanite_settings');n.enabled=True;n.explicit_tangents=True;n.fallback_percent_triangles=1.;n.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',n);save(mesh)
receipt['complete']=True;record();print('GUANLEI_V2_ASSETS_SAVED')
