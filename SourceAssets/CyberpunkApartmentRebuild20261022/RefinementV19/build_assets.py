"""Save V19 facade density, finite ad/projection assets and coherent water programs."""
from pathlib import Path
import unreal as u,json,runpy,gc,hashlib
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));BASE=C['BASE']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
H=runpy.run_path(str(R.parent/'RefinementV10/build_assets.py'));node=H['node'];wire=H['wire'];custom=H['custom'];param=H['param']
report=dict(stage='building',materials={},meshes={},textures={});previous=json.loads((R/'assets_saved.json').read_text()) if (R/'assets_saved.json').exists() else {}
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Missing V19 dependency '+p)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Asset save failed '+a.get_path_name())
def duplicate(name,source):
 path=BASE+'/Materials/'+name
 return load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,BASE+'/Materials',load(source))
def finish(key,m):
 errors=list(L.recompile_material(m))
 if errors:raise RuntimeError(str(errors))
 if L.get_statistics(m).get_editor_property('num_pixel_shader_instructions')<=0:raise RuntimeError('No shader program '+key)
 save(m);report['materials'][key]=m.get_path_name();record()
def fresh(name):
 path=BASE+'/Materials/'+name;m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m);return m
def texture(file,name,kind='color'):
 t=u.AssetImportTask();t.filename=str(file);t.destination_path=BASE+'/Textures';t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.TextureFactory();A.import_asset_tasks([t]);a=load(BASE+'/Textures/'+name)
 values=dict(srgb=kind!='glyph',compression_settings=u.TextureCompressionSettings.TC_BC7 if kind!='glyph' else u.TextureCompressionSettings.TC_MASKS,max_texture_size=1024 if kind=='glyph' else 2048,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
 if kind=='cube':values['lod_group']=u.TextureGroup.TEXTUREGROUP_SKYBOX
 if kind=='glyph':values.update(address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=True)
 for k,v in values.items():a.set_editor_property(k,v)
 save(a);report['textures'][name]=a.get_path_name();return a
def instance(key,parent,values={},color=None):
 name='MI_AP19_'+key;path=BASE+'/Materials/'+name;m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(m,parent)
 for k,v in values.items():L.set_material_instance_scalar_parameter_value(m,k,float(v))
 if color:L.set_material_instance_vector_parameter_value(m,'Tint',u.LinearColor(*color,1))
 L.update_material_instance(m);save(m);report['materials'][key]=m.get_path_name();return m
def facades():
 for family in C['FAMILIES']:
  tex=texture(R/'Textures'/f'T_AP19_{family}_E.png',f'T_AP19_{family}_E')
  m=duplicate('M_AP19_'+family,'/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV17/Materials/M_AP17_'+family)
  for n in L.get_material_expressions(m):
   if isinstance(n,u.MaterialExpressionTextureSample):
    t=n.get_editor_property('texture')
    if t and t.get_name().endswith('_E'):n.set_editor_property('texture',tex)
   if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='WindowGain':n.set_editor_property('default_value',1.05)
  finish(family,m)
 instance('FarQuietGlass',load(report['materials']['QuietGlass']),{'WindowGain':.35});record()
def additive(m,color,opacity):
 m.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE);m.set_editor_property('two_sided',False)
 bsdf=node(m,'SubstrateUnlitBSDF');wire(color,bsdf,'EmissiveColor');wire(node(m,'Constant3Vector',constant=u.LinearColor(1,1,1,1)),bsdf,'TransmittanceColor');L.connect_material_property(bsdf,'',u.MaterialProperty.MP_FRONT_MATERIAL)
 L.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR);L.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
def ads():
 for b in C['BOARDS']:
  m=duplicate('MI_AP19_Display_'+b['key'],'/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV16/Materials/MI_AP16_Nexus')
  for k,v in dict(Campaign=b['slot'],Phase=b['phase'],Aspect=b['w']/b['h'],PlaybackRate=1.).items():L.set_material_instance_scalar_parameter_value(m,k,v)
  L.update_material_instance(m);save(m);report['materials']['Display_'+b['key']]=m.get_path_name()
 # Reuse manufactured PBR and restrained trim lights; no dynamic light components.
 report['materials']['Metal']='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV7/Materials/M_AP7_Machined'
 for role,color in [('Warm',(1,.63,.28)),('Teal',(.12,.74,1)),('Violet',(.8,.32,1))]:instance(role,load('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV17/Materials/M_AP17_StructureLight'),{'Gain':.8},color)
 glyphs={}
 for b in C['HOLOGRAMS']:glyphs[b['key']]=texture(R/'Textures'/f"T_AP19_{b['key']}_Glyph.png",f"T_AP19_{b['key']}_Glyph",'glyph')
 m=fresh('M_AP19_Hologram');t=custom(m,'return Clock+Phase;',{'Clock':node(m,'Time'),'Phase':param(m,'Phase',0)},1)
 color=custom(m,(R/'Hologram.hlsl').read_text(),dict(UV=node(m,'TextureCoordinate'),T=t,Style=param(m,'Style',0),Tint=node(m,'VectorParameter',parameter_name='Tint',default_value=u.LinearColor(.12,.74,1,1)),Gain=param(m,'Gain',1.5),Night=H['night'](m),Glyph=node(m,'TextureObjectParameter',parameter_name='Glyph',texture=glyphs['Aether'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)))
 fade=node(m,'DepthFade',fade_distance_default=1000.,opacity_default=1.);color=custom(m,'return Color*Fade;',dict(Color=color,Fade=fade))
 additive(m,color,node(m,'Constant',r=1));finish('HologramMaster',m)
 for b in C['HOLOGRAMS']:
  mi=instance('Hologram_'+b['key'],m,dict(Style=b['style'],Phase=b['phase'],Gain=1.5),b['color']);L.set_material_instance_texture_parameter_value(mi,'Glyph',glyphs[b['key']]);L.update_material_instance(mi);save(mi)
 m=fresh('M_AP19_Projection');tint=node(m,'VectorParameter',parameter_name='Tint',default_value=u.LinearColor(.12,.74,1,1))
 mask=custom(m,'''float q=saturate(UV.x);float edge=pow(saturate(abs(dot(normalize(N),normalize(View)))),1.5);
float fade=smoothstep(0,.018,q)*(1-smoothstep(.76,1,q));
return edge*fade*(.96+.04*sin((Clock+Phase)*.22+q*4))*Night*Depth;''',dict(UV=node(m,'TextureCoordinate'),N=node(m,'VertexNormalWS'),View=node(m,'CameraVectorWS'),Clock=node(m,'Time'),Phase=param(m,'Phase',0),Night=H['night'](m),Depth=node(m,'DepthFade',fade_distance_default=1000.,opacity_default=1.)),1)
 color=custom(m,'return Tint*Gain*Mask;',dict(Tint=tint,Gain=param(m,'Gain',.22),Mask=mask));additive(m,color,node(m,'Constant',r=1));finish('ProjectionMaster',m)
 for b in C['HOLOGRAMS']:instance('Beam_'+b['key'],m,dict(Phase=b['phase'],Gain=.22),b['color'])
 record()
def meshes():
 for row in json.loads((R/'assembly.json').read_text())['meshes']:
  digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest();old=previous.get('meshes',{}).get(row['key'],{})
  if old.get('sha256')==digest and E.does_asset_exist(old['path']):report['meshes'][row['key']]=old;continue
  t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
  o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;o.import_mesh=True;o.import_materials=False;o.import_textures=False;o.import_animations=False;d=o.static_mesh_import_data
  for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():d.set_editor_property(k,v)
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=o;A.import_asset_tasks([t]);mesh=load(BASE+'/Meshes/'+row['name'])
  for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,load(report['materials'][str(s.material_slot_name).removeprefix('AP19_')]))
  settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;SM.set_lod_build_settings(mesh,0,settings)
  ns=mesh.get_editor_property('nanite_settings').copy();ns.enabled=row['nanite'];ns.explicit_tangents=True;ns.generate_fallback=u.NaniteGenerateFallback.ENABLED;ns.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;ns.fallback_percent_triangles=1.;mesh.set_editor_property('nanite_settings',ns)
  if row['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite production failed '+row['key'])
  save(mesh);report['meshes'][row['key']]=dict(path=mesh.get_path_name(),triangles=row['triangles'],sha256=digest,nanite=row['nanite']);record();gc.collect();u.SystemLibrary.collect_garbage();print('AP19_MESH_SAVED',row['key'])
 for path in report['materials'].values():
  if path.startswith(BASE):save(load(path))
def water():
 cube=texture(R/'T_AP19_CityReflection.dds','T_AP19_CityReflection','cube');m=duplicate('M_AP19_Water','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV18/Materials/M_AP18_Water');count=0
 for n in L.get_material_expressions(m):
  if isinstance(n,u.MaterialExpressionTextureSampleParameterCube) and str(n.get_editor_property('parameter_name'))=='BayReflection':n.set_editor_property('texture',cube)
  if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('description'))=='AP10 coherent billboard and sweeping beam water reflections':
   n.set_editor_property('code',(R/'WaterReflection.hlsl').read_text());pins=list(n.get_editor_property('inputs'))
   for i,b in enumerate(C['HOLOGRAMS']):
    key='Holo'+str(i)
    if not any(str(p.get_editor_property('input_name'))==key for p in pins):p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
   n.set_editor_property('inputs',pins)
   for i,b in enumerate(C['HOLOGRAMS']):
    key='Holo'+str(i);existing=next((x for x in L.get_material_expressions(m) if isinstance(x,u.MaterialExpressionTextureObjectParameter) and str(x.get_editor_property('parameter_name'))==key),None)
    tex=load(report['textures'][f"T_AP19_{b['key']}_Glyph"]);obj=existing or node(m,'TextureObjectParameter',parameter_name=key,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS);wire(obj,n,key)
   count+=1
 if count!=1:raise RuntimeError('Retained dynamic reflection branch changed')
 finish('WaterMaster',m);mi=duplicate('MI_AP19_Water','/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV18/Materials/MI_AP18_Water');L.set_material_instance_parent(mi,m);L.set_material_instance_texture_parameter_value(mi,'BayReflection',cube);L.update_material_instance(mi);save(mi);report['materials']['Water']=mi.get_path_name();record()
def main():
 facades();ads();meshes();water();report.update(stage='assets_saved',shader_compiled=True,new_dynamic_lights=0,new_tick_actors=0,new_capture_actors=0);record();print('AP19_ASSETS_SAVED')
if __name__=='__main__':main()
