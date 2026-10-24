from pathlib import Path
import unreal as u,json,runpy,traceback
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));BASE=C['BASE']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='building',materials={},masters=[],meshes={},reused_textures=[],game_run=False)
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing tower dependency '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Tower asset save failed '+a.get_path_name())
def node(m,kind,**props):
 n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin):
 names=list(L.get_material_expression_input_names(b));norm=lambda s:str(s).replace(' ','').replace('_','').lower();actual=next((str(n) for n in names if norm(n)==norm(pin)),pin)
 if not L.connect_material_expressions(a,'',b,actual):raise RuntimeError('Tower material pin '+pin+' available '+str(names))
def custom(m,code,inputs,width=3):
 n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)));pins=[]
 for name in inputs:p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 n.set_editor_property('inputs',pins)
 for name,value in inputs.items():wire(value,n,name)
 return n
def scalar(m,value):return node(m,'Constant',r=value)
def rgb(m,v):return node(m,'Constant3Vector',constant=u.LinearColor(*v,1))
def texture(m,path,uv,normal=False):
 tex=load(path)
 sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_MASKS if 'MASKS' in str(tex.get_editor_property('compression_settings')) else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
 n=node(m,'TextureSample',texture=tex,sampler_type=sampler);wire(uv,n,'UVs')
 if path not in report['reused_textures']:report['reused_textures'].append(path)
 return n
def begin(key):
 name='M_AP11_'+key;path=BASE+'/Materials/'+name
 m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
 m.set_editor_property('used_with_nanite',True);return m
def slab(m,color,normal,rough,metal,emission=None):
 s=node(m,'SubstrateShadingModels')
 for n,pin,prop in [(color,'BaseColor','BASE_COLOR'),(normal,'Normal','NORMAL'),(rough,'Roughness','ROUGHNESS'),(metal,'Metallic','METALLIC')]:wire(n,s,pin);L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+prop))
 if emission:wire(emission,s,'Emissive Color');L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
 L.connect_material_property(s,'',u.MaterialProperty.MP_FRONT_MATERIAL)
def finish(key,m):
 errors=L.recompile_material(m)
 if errors:raise RuntimeError(str(errors))
 save(m);report['materials'][key]=m.get_path_name();report['masters'].append(m.get_path_name());record()
def night(m):return custom(m,'return 1-smoothstep(-.08,.12,Sun.z);',{'Sun':node(m,'SkyAtmosphereLightDirection',light_index=0)},1)
def instance(key,parent,glow):
 name='MI_AP11_'+key;path=BASE+'/Materials/'+name
 mi=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
 L.set_material_instance_parent(mi,parent);L.set_material_instance_vector_parameter_value(mi,'Glow',u.LinearColor(*glow,1));L.update_material_instance(mi);save(mi);report['materials'][key]=mi.get_path_name()
def materials():
 for key,s in C['SURFACES'].items():
  m=begin(key);uv=node(m,'TextureCoordinate',u_tiling=1/s['period'],v_tiling=1/s['period'])
  n=texture(m,s['normal'],uv,True);n=custom(m,'return normalize(float3(N.xy*Strength,N.z));',{'N':n,'Strength':scalar(m,s['strength'])})
  r=texture(m,s['rough_tex'],uv);r=custom(m,'return lerp(Lo,Hi,R.r);',{'Lo':scalar(m,s['rough'][0]),'Hi':scalar(m,s['rough'][1]),'R':r},1)
  slab(m,rgb(m,s['color']),n,r,scalar(m,s['metal']));finish(key,m)
 m=begin('ResidentialGlass');uv=node(m,'TextureCoordinate');panel=node(m,'TextureCoordinate',coordinate_index=1)
 n=texture(m,C['SUB']+'01_Paints/T_Noise_N',uv,True);n=custom(m,'return normalize(float3(N.xy*.008,1));',{'N':n})
 glow=node(m,'VectorParameter',parameter_name='Glow',default_value=u.LinearColor(0,0,0,1))
 emission=custom(m,'float e=min(min(UV.x,1-UV.x),min(UV.y,1-UV.y));float reveal=smoothstep(0,.08,e);float ceiling=.18+.82*smoothstep(.05,.85,UV.y);return Glow.rgb*ceiling*reveal*Night;',{'UV':panel,'Glow':glow,'Night':night(m)})
 slab(m,rgb(m,(.013,.023,.034)),n,scalar(m,.17),scalar(m,.18),emission);finish('ResidentialGlass',m)
 for key,color in C['WINDOWS'].items():instance(key,m,color)
 m=begin('GuideLight');uv=node(m,'TextureCoordinate');n=texture(m,C['SUB']+'01_Paints/T_Noise_N',uv,True);n=custom(m,'return normalize(float3(N.xy*.025,1));',{'N':n})
 glow=node(m,'VectorParameter',parameter_name='Glow',default_value=u.LinearColor(.055,.35,.43,1));emission=custom(m,'return Glow.rgb*lerp(.04,1.35,Night);',{'Glow':glow,'Night':night(m)})
 slab(m,rgb(m,(.12,.14,.15)),n,scalar(m,.32),scalar(m,.1),emission);finish('GuideLight',m)
 for key,color in C['ACCENTS'].items():instance(key,m,color)
 record()
def meshes():
 for row in json.loads((R/'assembly.json').read_text())['meshes']:
  t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  d=opt.static_mesh_import_data
  for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,one_convex_hull_per_ucx=True).items():d.set_editor_property(k,v)
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=opt;A.import_asset_tasks([t]);mesh=load(row['asset'])
  for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,load(report['materials'][str(s.material_slot_name)]))
  settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;SM.set_lod_build_settings(mesh,0,settings)
  body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
  nanite=mesh.get_editor_property('nanite_settings').copy();nanite.enabled=True;nanite.explicit_tangents=True;nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED;nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;nanite.fallback_percent_triangles=1.;mesh.set_editor_property('nanite_settings',nanite)
  if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Tower Nanite build failed '+row['key'])
  save(mesh);report['meshes'][row['key']]=dict(path=mesh.get_path_name(),source_triangles=row['triangles'],authored_simple_boxes=row['simple_collision_boxes']);record()
def main():
 try:materials();meshes();report['stage']='assets_saved';record()
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
