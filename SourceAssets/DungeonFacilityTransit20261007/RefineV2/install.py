"""Import finished V2 portal assets and patch only portals and PPE cabinet rotation."""
import unreal as u
from pathlib import Path
import json,hashlib,importlib.util,traceback,runpy
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent;PROJECT=PARENT.parents[1];OWNER='FacilityTransit.PortalV2';BASE='/Game/Dungeons/FacilityTransit20261007/RefineV2'
CFG=json.loads((PARENT/'Config/layout.json').read_text('utf8'));MAN=json.loads((ROOT/'manifest.json').read_text('utf8'));ROLES=json.loads((ROOT/'materials.json').read_text('utf8'))
spec=importlib.util.spec_from_file_location('facility_import_support',PARENT/'install.py');I=importlib.util.module_from_spec(spec);spec.loader.exec_module(I)
R=I.R;E=R.E;A=R.A;L=R.L;AA=R.AA
report=dict(stage='preparing',saved_assets=[],maps=[],ppe_rotations=[],portal_actor_counts={},tests_run=False,rendered=False,game_run=False,production_registered=False)
def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
for k,v in dict(ROOT=ROOT,OWNER=OWNER,BASE=BASE,MAN=MAN,report=report,record=record).items():setattr(R,k,v)
def material(name,r,textures):
 path=r['existing_ue_path'];key=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()+':pbr-v2';m=R.reuse(path,key)
 if m:return
 m=A.create_asset(path.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew());m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
 slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels);slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
 def scalar(v):
  n=L.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
 def rgb(v):
  n=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*v,1));return n
 def sample(key,kind):
  n=L.create_material_expression(m,u.MaterialExpressionTextureSample);n.set_editor_property('texture',textures[key]);n.set_editor_property('sampler_type',kind);return n
 def connect(n,out,prop,pin):L.connect_material_property(n,out,prop);L.connect_material_expressions(n,out,slab,pin)
 if name=='TechLabels':
  base=sample('EquipmentLabels',u.MaterialSamplerType.SAMPLERTYPE_COLOR);bout='RGB';rough=scalar(.7);rout=''
 else:
  f=r['family'];tone=sample(f+'_Tone',u.MaterialSamplerType.SAMPLERTYPE_MASKS);base=L.create_material_expression(m,u.MaterialExpressionMultiply);L.connect_material_expressions(tone,'R',base,'A');L.connect_material_expressions(rgb(r['basecolor_linear']),'',base,'B');bout=''
  rough=sample(f+'_Roughness',u.MaterialSamplerType.SAMPLERTYPE_MASKS);rout='R';connect(sample(f+'_NormalDX',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),'RGB',u.MaterialProperty.MP_NORMAL,'Normal')
 connect(base,bout,u.MaterialProperty.MP_BASE_COLOR,'BaseColor');connect(rough,rout,u.MaterialProperty.MP_ROUGHNESS,'Roughness');connect(scalar(r['metallic']),'',u.MaterialProperty.MP_METALLIC,'Metallic');L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
 result=L.recompile_material(m)
 if result:raise RuntimeError('Material build failed '+name+': '+str(result))
 R.saved(m,key)
def materials():
 textures={}
 for file in sorted((ROOT/'Authored/Textures').glob('*.png')):
  name=file.stem.removeprefix('T_FT2_');path=BASE+'/Textures/'+file.stem;key=hashlib.sha256(file.read_bytes()).hexdigest();tex=R.reuse(path,key)
  if not tex:
   tex=R.imported(path,file);normal=name.endswith('NormalDX');color=name=='EquipmentLabels';tex.set_editor_property('srgb',color);tex.set_editor_property('never_stream',False);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD)
   tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_BC7 if color else u.TextureCompressionSettings.TC_MASKS)
   if normal:tex.set_editor_property('flip_green_channel',False)
   R.saved(tex,key)
  textures[name]=tex
 seen=set()
 for name,r in ROLES.items():
  path=r['existing_ue_path']
  if path.startswith(BASE+'/') and path not in seen:material(name,r,textures);seen.add(path)
def patch_map(path,themes):
 R.guard();world=u.EditorLoadingAndSavingUtils.load_map(path)
 if not world:raise RuntimeError('Subject map unavailable: '+path)
 for a in list(AA.get_all_level_actors()):
  if any(str(t).startswith('FacilityTransit.Theme.') for t in a.tags):AA.destroy_actor(a)
  elif isinstance(a,u.ColdSteelSceneContainer):
   id=str(a.get_editor_property('container_id'))
   if id.startswith('FacilityTransit20261007.PPE'):
    a.set_actor_rotation(u.Rotator(pitch=0,yaw=-180,roll=0),True);report['ppe_rotations'].append(dict(map=path,id=id,yaw=-180))
 for gate,theme in zip(CFG['gates'],themes):
  count=0
  for m in MAN['meshes']:
   if m['room']!=theme:continue
   a=R.static(m['mesh'],gate['position_m'],gate['route']+'_'+m['name'],m['collision'],gate['yaw_deg'],shadow=m['cast_shadow'],folder='Portals/'+gate['route']+'/'+theme)
   a.set_editor_property('tags',list(a.tags)+[u.Name('FacilityTransit.Theme.'+theme),u.Name('FacilityTransit.Route.'+gate['route']),u.Name(OWNER)]);count+=1
  report['portal_actor_counts'][theme]=count
 E.set_metadata_tag(world,OWNER+'.Revision','20261007-v2')
 runpy.run_path(str(PARENT.parent/'HallLighting20261007/profile.py'))['reapply_if_installed']()
 if not u.EditorLoadingAndSavingUtils.save_map(world,path):raise RuntimeError('Unable to save '+path)
 report['maps'].append(dict(path=path,saved=True,themes=themes));record()
def publish_source_manifest():
 parent=json.loads((PARENT/'manifest.json').read_text('utf8'));parent['meshes']=[m for m in parent['meshes'] if m['room']=='Hall']+MAN['meshes'];parent['active_refinement']=str(ROOT)
 (PARENT/'manifest.json').write_text(json.dumps(parent,indent=2),encoding='utf8')
 runpy.run_path(str(PARENT/'draft.py'),run_name='__main__');report['source_references_saved']=True
def main():
 R.guard();record();materials();R.meshes();report['stage']='assets_saved';record()
 for path,themes in zip((CFG['map'],CFG['alternate_map']),CFG['preview_sets']):patch_map(path,themes)
 publish_source_manifest()
 detail=PARENT/'RefineV3'
 if (detail/'Receipts/install.json').exists() and json.loads((detail/'Receipts/install.json').read_text('utf8')).get('stage')=='maps_saved':runpy.run_path(str(detail/'install.py'),run_name='__main__')
 report['stage']='maps_saved';record();u.log('FACILITY_PORTAL_V2_MAPS_SAVED')
if __name__=='__main__':
 try:main()
 except Exception:report['error']=traceback.format_exc();record();raise
