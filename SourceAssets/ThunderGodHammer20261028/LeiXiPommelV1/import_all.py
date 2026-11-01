"""Import Lei Xi production assets, then publish its exclusive modification option."""
from pathlib import Path
import unreal as u,json,shutil,os
P=Path(__file__).resolve().parent;R=P.parents[2]
D='/Game/Weapons/ThunderGodHammer20261028/LeiXiPommelV1'
ICON='ue_thunder_god_hammer_pommel_lei_xi_pommel'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
manifest=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))
receipt={'complete':False,'saved_assets':[],'source_mesh':manifest,'runtime_tested':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
 asset.modify()
 if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+asset.get_path_name())
 receipt['saved_assets'].append(asset.get_path_name());record();return asset
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
 if package.get_name().startswith(D+'/') or package.get_name().endswith('/'+ICON):raise RuntimeError('Preserve unsaved package '+package.get_name())
def imp(file,name,folder,options=None):
 t=u.AssetImportTask();t.filename=str(file);t.destination_name=name;t.destination_path=folder;t.automated=True;t.save=False;t.replace_existing=True;t.replace_existing_settings=True
 if options:t.options=options
 A.import_asset_tasks([t]);asset=u.load_asset(folder+'/'+name)
 if not asset:raise RuntimeError('Import failed '+name)
 return asset
record();texs={}
for key in ['MetalBaseColor','MetalNormal','MetalORM','CoreBaseColor','CoreEmission']:
 name='T_LeiXi_'+key;tex=imp(P/'Textures'/(name+'.png'),name,D+'/Textures');normal=key=='MetalNormal';color=key.endswith('BaseColor')
 tex.set_editor_property('srgb',color);tex.set_editor_property('flip_green_channel',normal)
 tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if color else u.TextureCompressionSettings.TC_MASKS)
 tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if normal else u.TextureGroup.TEXTUREGROUP_WEAPON)
 tex.set_editor_property('max_texture_size',2048);tex.set_editor_property('never_stream',False);tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
 texs[key]=save(tex)
def node(mat,cls):return L.create_material_expression(mat,cls)
def link(a,out,b,pin):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect material input '+pin)
def scalar(mat,value):
 n=node(mat,u.MaterialExpressionConstant);n.set_editor_property('r',value);return n
def sample(mat,key):
 n=node(mat,u.MaterialExpressionTextureSample);n.set_editor_property('texture',texs[key]);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='MetalNormal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if key.endswith('BaseColor') else u.MaterialSamplerType.SAMPLERTYPE_MASKS);return n
materials={'M_ThunderGodHammerSurface':u.load_asset('/Game/Weapons/ThunderGodHammer20261028/Materials/M_ThunderGodHammerSurface')}
for name,tint in [('M_LeiXi_ForgedSteel',(.20,.22,.25)),('M_LeiXi_SilverInlay',(1.55,1.47,1.29)),('M_LeiXi_AgedSeams',(.70,.47,.26)),('M_LeiXi_StormCore',(1,1,1))]:
 core=name.endswith('StormCore');mat=u.load_asset(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat)
 mat.set_editor_property('used_with_nanite',True);mat.set_editor_property('two_sided',False)
 surface=node(mat,u.MaterialExpressionSubstrateShadingModels);surface.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
 color=sample(mat,'CoreBaseColor' if core else 'MetalBaseColor');tv=node(mat,u.MaterialExpressionConstant3Vector);tv.set_editor_property('constant',u.LinearColor(*tint,1));mul=node(mat,u.MaterialExpressionMultiply);link(color,'RGB',mul,'A');link(tv,'',mul,'B')
 norm=sample(mat,'MetalNormal');orm=sample(mat,'MetalORM')
 for n,out,pin,prop in [(mul,'','BaseColor',u.MaterialProperty.MP_BASE_COLOR),(norm,'RGB','Normal',u.MaterialProperty.MP_NORMAL),(scalar(mat,.3 if core else .94),'','Metallic',u.MaterialProperty.MP_METALLIC),(scalar(mat,.22) if core else orm,'' if core else 'G','Roughness',u.MaterialProperty.MP_ROUGHNESS)]:
  link(n,out,surface,pin);L.connect_material_property(n,out,prop)
 if core:
  emission=sample(mat,'CoreEmission');active=node(mat,u.MaterialExpressionScalarParameter);active.set_editor_property('parameter_name','LeiXiActive');active.set_editor_property('default_value',0.)
  clock=node(mat,u.MaterialExpressionTime);pulse=node(mat,u.MaterialExpressionCustom);pulse.set_editor_property('code','return (3.0 + Active * 9.0) * (0.88 + 0.12 * sin(T * 7.0));');pulse.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
  entries=[]
  for x in ['Active','T']:e=u.CustomInput();e.set_editor_property('input_name',x);entries.append(e)
  pulse.set_editor_property('inputs',entries);link(active,'',pulse,'Active');link(clock,'',pulse,'T')
  glow=node(mat,u.MaterialExpressionMultiply);link(emission,'RGB',glow,'A');link(pulse,'',glow,'B');link(glow,'',surface,'Emissive Color');L.connect_material_property(glow,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
 if not L.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output')
 L.layout_material_expressions(mat);errors=L.recompile_material(mat)
 if errors:raise RuntimeError(str(errors))
 materials[name]=save(mat)
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
mesh=imp(P/'Export'/(manifest['mesh']+'.fbx'),manifest['mesh'],D+'/Meshes',opt)
for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,materials[str(s.material_slot_name)])
settings=mesh.get_editor_property('nanite_settings');settings.enabled=True;settings.explicit_tangents=True;settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',settings)
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);build=sub.get_lod_build_settings(mesh,0)
build.set_editor_property('use_full_precision_u_vs',True);build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_normals',False);build.set_editor_property('recompute_tangents',True);build.set_editor_property('use_mikk_t_space',True);sub.set_lod_build_settings(mesh,0,build);save(mesh)
icon=imp(P/'lei_xi_pommel_icon.png',ICON,'/Game/ColdSteelData/AttachmentIcons20260913')
icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);icon.set_editor_property('srgb',True);icon.set_editor_property('never_stream',True);icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);icon.set_editor_property('max_texture_size',1024);save(icon)
shutil.copy2(P/'lei_xi_pommel_icon.png',R/'Content/ColdSteelData/AttachmentIcons20260913'/(ICON+'.png'))
def publish(path,edit):
 original=path.read_text(encoding='utf-8-sig');data=json.loads(original);edit(data)
 backup=P/'BeforePublication'/path.name;backup.parent.mkdir(exist_ok=True)
 if not backup.exists():backup.write_text(original,encoding='utf-8')
 if path.read_text(encoding='utf-8-sig')!=original:raise RuntimeError('Concurrent edit: '+str(path))
 temp=path.with_suffix('.lei_xi.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(temp,path)
def option(data):
 column=next(c for c in data['columns'] if c['key']=='pommel');column['options']=[o for o in column['options'] if o['id']!='lei_xi_pommel']
 column['options'].append({'id':'lei_xi_pommel','name':'雷息配重','tier':'special','weapons':['ue_thunder_god_hammer'],
  'description':'雷神之锤专属。多面锻钢配重收拢雷能，菱形雷窗与嵌银回流编结接续原厂接颈。',
  'appearance':'原厂编纹接颈 · 菱形内藏雷核 · 嵌银回流编结',
  'stats':{'attack_speed_mult':1.15,'stamina_mult':.85},
  'effects':[{'text':'攻击速度+15%','benefit':1},{'text':'体力消耗-15%','benefit':1}],
  'special_effects':['雷息激励｜使用此武器造成有效雷电伤害时，获得10秒魔法激励（攻击速度提高25%）；再次触发刷新为10秒，不叠加。','雷能回流｜包括闪电、雷电领域、武器附加闪电、雷神之锤重击雷击、贯雷落地雷击、疾雷落雷和感电过载。普通物理命中不触发。']})
def module(data):
 data['slots']['pommel']['lei_xi_pommel']={'mesh':mesh.get_path_name(),'location_cm':manifest['location_cm'],'appearance':'原厂接颈 · 四面菱形雷窗 · 嵌银回流编结','interface':'thunder_god_hammer_modular_v1','model_revision':'LeiXiPommelV1'}
publish(R/'Content/ColdSteelData/thunder-god-hammer-gunsmith.json',option)
publish(R/'Content/ColdSteelData/thunder-god-hammer-modules.json',module)
receipt['complete']=True;receipt['mesh']=mesh.get_path_name();receipt['icon']=icon.get_path_name();receipt['catalog_published']=True;record()
print('LEIXI_POMMEL_IMPORTED_SAVED_AND_PUBLISHED')
