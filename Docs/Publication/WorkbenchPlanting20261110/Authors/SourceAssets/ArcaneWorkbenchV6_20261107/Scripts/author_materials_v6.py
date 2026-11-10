"""Author V6 PBR materials in a background commandlet; preserve all other assets."""
import unreal as u,json,re,runpy
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ArcaneWorkbenchV6_20261107')
DEST='/Game/Building/ArcaneWorkbenchV6_20261107'
patch_rune_material=runpy.run_path(str(R/'Scripts/patch_ritual_pulse_v6.py'))['patch_rune_material']
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
assert Path(u.Paths.project_dir()).resolve()==R.parents[1].resolve()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE running')
recipe=json.loads((R/'Input/UE_Material_Recipe.json').read_text(encoding='utf-8'))
dirty=u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
if any(p.get_path_name().startswith(DEST) for p in dirty):raise RuntimeError('Target contains unsaved edits')
receipt={'stage':'authoring_materials','textures':{},'materials':{},'tests_run':False,'renders_run':False}
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed: '+a.get_path_name())
def node(m,cls):return L.create_material_expression(m,cls)
def scalar(m,v):
 n=node(m,u.MaterialExpressionConstant);n.set_editor_property('r',float(v));return n
def vec(m,v):
 n=node(m,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*v[:3],1));return n
def link(n,p,t,i):
 if not L.connect_material_expressions(n,p,t,i):raise RuntimeError('Failed material link '+i)
def output(n,p,prop):
 if not L.connect_material_property(n,p,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Failed material property '+prop)
def mul(m,n,p,f):
 x=node(m,u.MaterialExpressionMultiply);link(n,p,x,'A');link(scalar(m,f),'',x,'B');return x
specs={}
for m in recipe['materials']:
 for key,data in m['inputs'].items():
  t=data.get('texture') or data.get('normal_color',{}).get('texture')
  if t:
   spec={'file':t['file'],'srgb':bool(t['srgb']),'normal':key=='Normal'}
   if t['file'] in specs:assert specs[t['file']]==spec
   specs[t['file']]=spec
textures={}
for filename,spec in specs.items():
 name='T_AW_'+Path(filename).stem;path=DEST+'/Textures/'+name
 tex=u.load_asset(path)
 if not tex:
  task=u.AssetImportTask();task.filename=str(R/'Input'/filename);task.destination_path=DEST+'/Textures';task.destination_name=name;task.automated=True;task.save=False;task.replace_existing=False
  A.import_asset_tasks([task]);tex=u.load_asset(path)
 if not tex:raise RuntimeError('Texture import failed: '+filename)
 tex.set_editor_property('srgb',spec['srgb'])
 tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if spec['normal'] else u.TextureCompressionSettings.TC_DEFAULT if spec['srgb'] else u.TextureCompressionSettings.TC_MASKS)
 tex.set_editor_property('flip_green_channel',spec['normal'])
 tex.set_editor_property('never_stream',False)
 assert tex.get_editor_property('srgb')==spec['srgb'] and tex.get_editor_property('flip_green_channel')==spec['normal']
 save(tex);textures[filename]=tex
 receipt['textures'][filename]={'asset':tex.get_path_name(),'srgb':tex.get_editor_property('srgb'),'flip_green_channel':tex.get_editor_property('flip_green_channel'),'compression':str(tex.get_editor_property('compression_settings'))}
(R/'Receipts/textures.json').write_text(json.dumps(receipt['textures'],indent=2),encoding='utf-8')
def expression(m,data,normal=False):
 if 'texture' in data:
  n=node(m,u.MaterialExpressionTextureSample);n.set_editor_property('texture',textures[data['texture']['file']]);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR if data['texture']['srgb'] else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
  return n,'RGB' if normal or data['texture']['srgb'] else 'R'
 v=data['constant'];return (vec(m,v),'') if isinstance(v,list) else (scalar(m,v),'')
def canon(s):return re.sub('[^a-z0-9]','',s.lower())
bindings={}
for spec in recipe['materials']:
 name=spec['ue_safe_name'];path=DEST+'/Materials/'+name
 mat=u.load_asset(path)
 if mat is None:mat=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
 if mat is None:raise RuntimeError('Material creation failed: '+name)
 L.delete_all_material_expressions(mat)
 inp=spec['inputs'];trans=float(inp['Transmission Weight']['constant']);ior=float(inp['IOR']['constant']);alpha=float(inp['Alpha']['constant'])
 mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT if trans>0 else u.BlendMode.BLEND_OPAQUE)
 mat.set_editor_property('two_sided',spec['slot'] in [17,20,21,27])
 for key,prop in [('Base Color','BASE_COLOR'),('Metallic','METALLIC'),('Roughness','ROUGHNESS')]:
  n,p=expression(mat,inp[key]);output(n,p,prop)
 normal=inp['Normal']
 if 'normal_color' in normal:
  n,p=expression(mat,normal['normal_color'],True);strength=normal['normal_strength']
  if abs(strength-1)>1e-6:
   scaled=node(mat,u.MaterialExpressionMultiply);link(n,p,scaled,'A');link(vec(mat,[strength,strength,1]),'',scaled,'B');n=node(mat,u.MaterialExpressionNormalize);link(scaled,'',n,'VectorInput');p=''
  output(n,p,'NORMAL')
 emission=float(inp['Emission Strength']['constant'])
 if emission>0:
  n,p=expression(mat,inp['Emission Color']);output(mul(mat,n,p,emission),'','EMISSIVE_COLOR')
 if trans>0:
  mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
  mat.set_editor_property('refraction_method',u.RefractionMode.RM_INDEX_OF_REFRACTION)
  output(scalar(mat,ior),'','REFRACTION')
  # UE default-lit translucency maps Blender transmission to inverse opacity,
  # with IOR-derived dielectric Fresnel to preserve visible grazing highlights.
  f=node(mat,u.MaterialExpressionFresnel);f.set_editor_property('exponent',5.0);f.set_editor_property('base_reflect_fraction',((ior-1)/(ior+1))**2)
  x=mul(mat,f,'',trans*alpha);add=node(mat,u.MaterialExpressionAdd);link(x,'',add,'A');link(scalar(mat,(1-trans)*alpha),'',add,'B');output(add,'','OPACITY')
 patch_rune_material(mat)
 L.layout_material_expressions(mat);L.recompile_material(mat);save(mat)
 assert mat.get_editor_property('blend_mode')==(u.BlendMode.BLEND_TRANSLUCENT if trans>0 else u.BlendMode.BLEND_OPAQUE)
 bindings[canon(spec['material_name'])]=mat
 receipt['materials'][name]={'asset':mat.get_path_name(),'slot_recipe':spec['slot'],'blend_mode':str(mat.get_editor_property('blend_mode')),'emission_strength':emission,'transmission':trans,'ior':ior,'normal_strength':normal.get('normal_strength')}
(R/'Receipts/materials.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
mesh=u.load_asset(DEST+'/Meshes/SM_ArcaneWorkbench_V6')
if mesh is None:raise RuntimeError('Import mesh before binding')
if len(mesh.static_materials)!=28:raise RuntimeError('Unexpected slot count')
for i,s in enumerate(mesh.static_materials):
 k=canon(str(s.get_editor_property('imported_material_slot_name')));k2=canon(str(s.material_slot_name))
 mat=bindings.get(k) or bindings.get(k2)
 if mat is None:raise RuntimeError('Unknown material slot '+str(s.get_editor_property('imported_material_slot_name')))
 mesh.set_material(i,mat)
 if mesh.get_material(i)!=mat:raise RuntimeError('Material binding did not persist')
mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
save(mesh)
receipt['stage']='materials_bound';receipt['mesh']=mesh.get_path_name();receipt['bound_slots']=[mesh.get_material(i).get_path_name() for i in range(28)]
receipt['translucency_note']='Legacy UE Default Lit with Surface ForwardShading, IOR refraction, inverse transmission opacity plus IOR-derived Fresnel. Cross-renderer approximation; no game/visual validation.'
receipt['nanite_note']='Nanite not enabled for the single combined mesh with 5 translucent material slots; no automatic geometry reduction or LOD authored.'
(R/'Receipts/materials.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({'stage':receipt['stage'],'textures':len(textures),'materials':len(bindings),'mesh':mesh.get_path_name()}))
desc=mesh.get_static_mesh_description(0)
if desc is None:raise RuntimeError('Source mesh description unavailable for socket alignment')
points=[]
for i in range(8):
 v=desc.get_vertex_position(u.VertexID(i));points.append([v.x,v.y,v.z])
geo={'first_vertices':points,'vertices':desc.get_vertex_count(),'triangles':desc.get_triangle_count()}
(R/'Receipts/imported-geometry.json').write_text(json.dumps(geo,indent=2),encoding='utf-8')
print(json.dumps(geo))