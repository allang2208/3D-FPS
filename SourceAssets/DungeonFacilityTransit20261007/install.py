"""Background-only save of connected subject maps and all six authored portal kits.
The reception original and the live randomized dungeon catalog are never saved here.
"""
import unreal as u
import json,hashlib,math,importlib.util,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
CFG=json.loads((ROOT/'Config/layout.json').read_text('utf8'));MAN=json.loads((ROOT/'manifest.json').read_text('utf8'));ROLES=json.loads((ROOT/'Config/materials.json').read_text('utf8'));BASE=CFG['base'];OWNER='FacilityTransit20261007'
# Reuse the accepted importer and native interaction assembly; no old main() is run.
source=PROJECT/'SourceAssets/DungeonReceptionHall20261006/install.py'
spec=importlib.util.spec_from_file_location('reception_import_support',source);R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
for k,v in dict(ROOT=ROOT,PROJECT=PROJECT,CFG=CFG,MAN=MAN,ROLES=ROLES,BASE=BASE,OWNER=OWNER,MAP=CFG['map']).items():setattr(R,k,v)
E=R.E;A=R.A;L=R.L;AA=R.AA
report=dict(stage='preparing',saved_assets=[],maps=[],interactions=[],lights=0,reused_placements=0,instance_groups=[],tests_run=False,rendered=False,game_run=False,editor_opened=False,production_registered=False)
R.report=report
OFFSET=CFG['offset_m']
def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
R.record=record
def spawn(cls,p,label,folder='Architecture',yaw=0):
 worldp=[p[i]+OFFSET[i] for i in range(3)]
 a=AA.spawn_actor_from_class(cls,R.vec(worldp),u.Rotator(pitch=0,yaw=-yaw,roll=0))
 if not a:raise RuntimeError('Unable to create '+label)
 a.set_actor_label('FacilityTransit_'+label);a.set_folder_path('FacilityTransit/'+folder)
 a.set_editor_property('tags',list(a.tags)+[u.Name('FacilityTransit.Subject')]);return a
R.spawn=spawn
native=source.read_text('utf8');native=native[native.index('def interactions():'):native.index('def build_map():')].replace("'/Meshes/SM_Reception_'","'/Meshes/SM_FT_'")
exec(compile(native,'facility_native_interactions','exec'),R.__dict__)
# Permit scoped author revisions of this task's own imported FBX after its subject exists.
mesh_import=source.read_text('utf8');mesh_import=mesh_import[mesh_import.index('def meshes():'):mesh_import.index('def interactions():')]
mesh_import=mesh_import.replace(" or E.does_asset_exist(MAP)"," or not E.get_metadata_tag(m,OWNER+'.Source')")
exec(compile(mesh_import,'facility_mesh_import','exec'),R.__dict__)

def materials():
 file=ROOT/'Authored/Textures/T_FT_Wayfinding.png';key=hashlib.sha256(file.read_bytes()).hexdigest();path=BASE+'/Textures/T_FT_Wayfinding';tex=R.reuse(path,key)
 if not tex:
  tex=R.imported(path,file);tex.set_editor_property('srgb',True);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD);R.saved(tex,key)
 for name,r in ROLES.items():
  if not r.get('new_authored'):continue
  path=r['existing_ue_path'];key=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()+':substrate-v1';m=R.reuse(path,key)
  if m:continue
  m=A.create_asset(path.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew())
  m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
  slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels);slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
  def scalar(v):
   n=L.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
  def rgb(v):
   n=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*v,1));return n
  def connect(n,out,prop,pin):L.connect_material_property(n,out,prop);L.connect_material_expressions(n,out,slab,pin)
  if name=='Labels':
   c=L.create_material_expression(m,u.MaterialExpressionTextureSample);c.set_editor_property('texture',tex);c.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR);out='RGB'
  else:c=rgb(r['basecolor_linear']);out=''
  connect(c,out,u.MaterialProperty.MP_BASE_COLOR,'BaseColor');connect(scalar(r['roughness']),'',u.MaterialProperty.MP_ROUGHNESS,'Roughness');connect(scalar(r['metallic']),'',u.MaterialProperty.MP_METALLIC,'Metallic');L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
  result=L.recompile_material(m)
  if result:raise RuntimeError('Required material build failed '+str(result))
  R.saved(m,key)

def fixture_light(p,prefix='Hall'):
 spot=p.get('type')=='spot';a=spawn(u.SpotLight if spot else u.PointLight,p['position_m'],prefix+'_'+p['id'],'Lighting')
 if spot:a.set_actor_rotation(u.Rotator(pitch=-90,yaw=0,roll=0),True)
 c=a.get_component_by_class(u.PointLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE);c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(p['intensity']);c.set_editor_property('attenuation_radius',p['radius']*100);c.set_editor_property('cast_shadows',p['cast_shadows'])
 c.set_editor_property('max_draw_distance',4200 if spot else 2300);c.set_editor_property('max_distance_fade_range',600);c.set_editor_property('source_radius',8.);c.set_editor_property('source_length',60.);c.set_editor_property('indirect_lighting_intensity',.85);c.set_light_color(u.LinearColor(1,.94,.84,1))
 if spot:c.set_editor_property('outer_cone_angle',p['outer_cone_degrees']);c.set_editor_property('inner_cone_angle',p['inner_cone_degrees'])
 a.set_editor_property('tags',list(a.tags)+[u.Name('DungeonLight.'+p.get('role','Local'))]);report['lights']+=1
def rotate(p,yaw):
 a=math.radians(yaw);return [p[0]*math.cos(a)-p[1]*math.sin(a),p[0]*math.sin(a)+p[1]*math.cos(a),p[2]]
def gate(theme,p):
 for item in MAN['meshes']:
  if item['room']!=theme:continue
  a=R.static(item['mesh'],p['position_m'],p['route']+'_'+item['name'],item['collision'],p['yaw_deg'],shadow=item['cast_shadow'],folder='Portals/'+p['route']+'/'+theme)
  a.set_editor_property('tags',list(a.tags)+[u.Name('FacilityTransit.Theme.'+theme),u.Name('FacilityTransit.Route.'+p['route'])])
 for j,local in enumerate(((0,-.70,4.22),(0,2,2.47))):
  d=rotate(local,p['yaw_deg']);pos=[p['position_m'][i]+d[i] for i in range(3)]
  fixture_light(dict(id=p['route']+'_'+str(j),position_m=pos,intensity=1600 if j==0 else 1000,radius=4.8 if j==0 else 3.2,cast_shadows=False,type='point'),theme)

def build_map(path,themes,alternate=False):
 R.guard()
 if E.does_asset_exist(path):
  # Only a prior incomplete run of this script may resume this exact subject.
  existing=R.asset(path)
  if E.get_metadata_tag(existing,OWNER+'.Owner')!=OWNER:raise RuntimeError('Preserve existing unrelated map '+path)
 else:
  existing=E.duplicate_asset(CFG['reception_source'],path)
  if not existing:raise RuntimeError('Reception map duplicate failed')
  E.set_metadata_tag(existing,OWNER+'.Owner',OWNER)
 world=u.EditorLoadingAndSavingUtils.load_map(path)
 if not world:raise RuntimeError('Unable to load new subject '+path)
 # The source reception cap has both ends in one mesh. Replace it with our retained west cap.
 for a in list(AA.get_all_level_actors()):
  label=a.get_actor_label()
  if label.startswith('FacilityTransit_') or u.Name('FacilityTransit.Subject') in a.tags or label=='Reception_SM_Reception_PreviewCaps':AA.destroy_actor(a)
 for item in MAN['meshes']:
  if item['room']!='Hall' or item['kind'] in ('Glass','Fracture'):continue
  R.static(item['mesh'],[0,0,0],item['name'],item['collision'],shadow=item['cast_shadow'],rail=item['kind']=='Rails',folder='PreviewOnly' if item['preview_only'] else 'Architecture')
 groups={}
 for p in CFG['parts']:
  a=R.static(p['mesh'],p['position_m'],p['id'],p['collision'],p['yaw_deg'],p['scale'],p['cast_shadow'],'ReusedFurniture');report['reused_placements']+=1
  a.set_editor_property('tags',list(a.tags)+[u.Name('ColdSteel.MainPlaza.Generated')]);groups.setdefault((p['mesh'],p['collision']),[]).append(a)
 for (mesh,col),actors in groups.items():
  if len(actors)<2:
   for a in actors:a.set_editor_property('tags',[u.Name('FacilityTransit.Subject')])
   continue
  c=u.PlazaInstanceTools.create_plaza_cluster(actors,'FacilityTransit_Instances_'+mesh.rsplit('/',1)[1])
  if c:
   c.set_editor_property('tags',[u.Name('FacilityTransit.Subject')]);c.set_folder_path('FacilityTransit/ReusedFurniture')
   for a in actors:AA.destroy_actor(a)
   report['instance_groups'].append(dict(mesh=mesh,count=len(actors),map=path))
  else:
   for a in actors:a.set_editor_property('tags',[u.Name('FacilityTransit.Subject')])
 R.interactions()
 for p in CFG['lights']:fixture_light(p)
 for p,theme in zip(CFG['gates'],themes):gate(theme,p)
 # Alternate starts at the new concourse for convenient access to the other three kits.
 if alternate:
  for a in AA.get_all_level_actors():
   if isinstance(a,u.PlayerStart):
    a.set_actor_location(R.vec([39,0,1.1]),False,False);a.set_actor_rotation(u.Rotator(pitch=0,yaw=0,roll=0),True)
 E.set_metadata_tag(world,OWNER+'.Owner',OWNER);E.set_metadata_tag(world,OWNER+'.Revision',CFG['revision']);E.set_metadata_tag(world,OWNER+'.PreviewThemes',json.dumps(dict(zip(('Route1','Route2','Route3'),themes))))
 import runpy
 runpy.run_path(str(PROJECT/'SourceAssets/HallLighting20261007/profile.py'))['reapply_if_installed']()
 if not u.EditorLoadingAndSavingUtils.save_map(world,path):raise RuntimeError('Unable to save '+path)
 report['maps'].append(dict(path=path,saved=True,themes=themes,reception_connected=True));record()

def main():
 R.guard();record();materials();R.meshes();report['stage']='assets_saved';record()
 build_map(CFG['map'],CFG['preview_sets'][0]);build_map(CFG['alternate_map'],CFG['preview_sets'][1],True)
 botanical=ROOT/'BotanicalDisplay'
 if (botanical/'Receipts/install.json').exists() and json.loads((botanical/'Receipts/install.json').read_text('utf8')).get('stage')=='maps_saved':
  import runpy
  runpy.run_path(str(botanical/'install.py'),run_name='__main__')
 detail=ROOT/'RefineV3'
 if (detail/'Receipts/install.json').exists() and json.loads((detail/'Receipts/install.json').read_text('utf8')).get('stage')=='maps_saved':
  import runpy
  runpy.run_path(str(detail/'install.py'),run_name='__main__')
 report['stage']='maps_saved';record();u.log('FACILITY_TRANSIT_MAPS_SAVED')
if __name__=='__main__':
 try:
  refined=ROOT/'RefineV2'
  if (refined/'Receipts/install.json').exists() and json.loads((refined/'Receipts/install.json').read_text('utf8')).get('stage')=='maps_saved':
   import runpy
   runpy.run_path(str(refined/'install.py'),run_name='__main__')
  else:main()
 except Exception:report['error']=traceback.format_exc();record();raise
