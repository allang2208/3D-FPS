"""Apartment-only synchronized presentation clock and requested saved-map audit."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,hashlib,shutil
R=Path(__file__).resolve().parent;PROJECT=R.parents[2];BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV21';MAP='/Game/GameMaps/L_CyberpunkApartment'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def wire(a,b,pin):
 if not L.connect_material_expressions(a,'',b,str(pin)):raise RuntimeError('Clock connection failed '+str(pin))
def bind_existing_fixtures(world):
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)};changed=[]
 for atmosphere in actors.values():
  if not isinstance(atmosphere,u.ApartmentAtmosphere):continue
  bindings=list(atmosphere.get_editor_property('lights'))
  for i,b in enumerate(bindings):
   light=b.get_editor_property('actor')
   if not light or b.get_editor_property('fixtures'):continue
   label=light.get_actor_label();fixture=None
   if label.startswith('AP9_') and label.endswith('_Spot'):fixture=actors.get(label[:-5]+'_Head')
   elif label.startswith('AP_Light_Dining_'):fixture=actors.get('AP_PracticalLights')
   if fixture:
    b.set_editor_property('fixtures',[fixture]);bindings[i]=b;changed.append(dict(light=label,fixture=fixture.get_actor_label()))
  atmosphere.modify();atmosphere.set_editor_property('lights',bindings)
 return changed

def clock_assets(world):
 path=BASE+'/MPC_ApartmentClock';collection=u.load_asset(path)
 if not collection:
  collection=A.create_asset('MPC_ApartmentClock',BASE,u.MaterialParameterCollection,u.MaterialParameterCollectionFactoryNew())
  p=u.CollectionScalarParameter();p.set_editor_property('parameter_name','ServerTimeOffset');p.set_editor_property('default_value',0.);collection.set_editor_property('scalar_parameters',[p]);save(collection)
 receipt=R/'assets_saved.json'
 report=json.loads(receipt.read_text()) if receipt.exists() else dict(materials={},bindings=[],masters=[])
 report.update(stage='building',collection=collection.get_path_name());cache={}
 def convert(source):
  if not source:return source
  path=source.get_path_name()
  if path.startswith(BASE):return source
  if path in cache:return cache[path]
  if isinstance(source,u.MaterialInstanceConstant):
   parent=source.get_editor_property('parent');new_parent=convert(parent)
   if new_parent==parent:cache[path]=source;return source
   name='MI_AP21_'+source.get_name()+'_'+hashlib.sha1(path.encode()).hexdigest()[:8]
   m=u.load_asset(BASE+'/Materials/'+name) or A.duplicate_asset(name,BASE+'/Materials',source)
   L.set_material_instance_parent(m,new_parent);L.update_material_instance(m);save(m)
  elif isinstance(source,u.Material):
   times=[n for n in L.get_material_expressions(source) if isinstance(n,u.MaterialExpressionTime)]
   if not times:cache[path]=source;return source
   name='M_AP21_'+source.get_name()+'_'+hashlib.sha1(path.encode()).hexdigest()[:8]
   m=u.load_asset(BASE+'/Materials/'+name) or A.duplicate_asset(name,BASE+'/Materials',source)
   if E.get_metadata_tag(m,'AP21.Clock')!='1':
    originals=list(L.get_material_expressions(m));count=0
    for clock in [n for n in originals if isinstance(n,u.MaterialExpressionTime)]:
     if clock.get_editor_property('ignore_pause'):raise RuntimeError('Pause-independent source requires explicit clock: '+path)
     users=[]
     for dest in originals:
      names=L.get_material_expression_input_names(dest);inputs=L.get_inputs_for_material_expression(m,dest)
      users.extend((dest,pin) for pin,src in zip(names,inputs) if src==clock)
     shifted=L.create_material_expression(m,u.MaterialExpressionAdd);offset=L.create_material_expression(m,u.MaterialExpressionCollectionParameter)
     offset.set_editor_property('collection',collection);offset.set_editor_property('parameter_name','ServerTimeOffset');wire(clock,shifted,'A');wire(offset,shifted,'B')
     replacement=shifted
     if clock.get_editor_property('override_period') and clock.get_editor_property('period')>0:
      period=clock.get_editor_property('period');clock.set_editor_property('override_period',False)
      mod=L.create_material_expression(m,u.MaterialExpressionFmod);divisor=L.create_material_expression(m,u.MaterialExpressionConstant);divisor.set_editor_property('r',period);wire(shifted,mod,'A');wire(divisor,mod,'B');replacement=mod
     for dest,pin in users:wire(replacement,dest,pin)
     for prop in [u.MaterialProperty.MP_EMISSIVE_COLOR,u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_OPACITY]:
      if L.get_material_property_input_node(m,prop)==clock:L.connect_material_property(replacement,'',prop)
     count+=1
    E.set_metadata_tag(m,'AP21.Clock','1');E.set_metadata_tag(m,'AP21.Source',path)
   errors=list(L.recompile_material(m))
   if errors:raise RuntimeError(str(errors))
   if L.get_statistics(m).get_editor_property('num_pixel_shader_instructions')<=0:raise RuntimeError('Clock shader not produced '+name)
   save(m)
   report['masters']=[row for row in report['masters'] if row['source']!=path]
   report['masters'].append(dict(source=path,path=m.get_path_name(),time_nodes=len(times)))
  else:cache[path]=source;return source
  cache[path]=m;report['materials'][path]=m.get_path_name();return m
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  if isinstance(actor,u.ApartmentAtmosphere):actor.modify();actor.set_editor_property('animation_clock',collection)
  if not actor.get_actor_label().startswith(('BAY_','AP8_','AP9_','AP16_','AP19_')):continue
  for comp in actor.get_components_by_class(u.StaticMeshComponent):
   for slot,old in enumerate(comp.get_materials()):
    new=convert(old)
    if new!=old:
     actor.modify();comp.set_material(slot,new)
     report['bindings']=[row for row in report['bindings'] if (row['actor'],row['component'],row['slot'])!=(actor.get_actor_label(),comp.get_name(),slot)]
     report['bindings'].append(dict(actor=actor.get_actor_label(),component=comp.get_name(),slot=slot,source=old.get_path_name(),material=new.get_path_name()))
 report['stage']='assets_saved';(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8');return report
def apply_upgrade(world):
 bind_existing_fixtures(world)
 report=json.loads((R/'assets_saved.json').read_text());actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
 for actor in actors.values():
  if isinstance(actor,u.ApartmentAtmosphere):actor.modify();actor.set_editor_property('animation_clock',u.load_asset(report['collection']))
 restored=[]
 for row in report['bindings']:
  actor=actors.get(row['actor'])
  if not actor:continue
  comp=next((c for c in actor.get_components_by_class(u.StaticMeshComponent) if c.get_name()==row['component']),None)
  if not comp:continue
  old=comp.get_material(row['slot'])
  if old and old.get_path_name() in [row['source'],row['material']]:actor.modify();comp.set_material(row['slot'],u.load_asset(row['material']));restored.append(row['actor'])
 result=dict(clock_material_slots=len(restored))
 bedroom=R.parent/'BedroomPilot20261024/Integration20261024'
 if (bedroom/'installed.json').exists():
  import runpy
  result['bedroom']=runpy.run_path(str(bedroom/'install_level.py'))['apply_upgrade'](world)
 exterior=PROJECT/'SourceAssets/CyberpunkExteriorUpgrade20261025'
 if (exterior/'installed.json').exists():
  import runpy
  result['exterior']=runpy.run_path(str(exterior/'install_level.py'))['apply_upgrade'](world)
 kitchen_repair=PROJECT/'SourceAssets/CyberpunkKitchenRepair20261026'
 if (kitchen_repair/'installed.json').exists() and 'KP_Counter' in actors:
  import runpy
  result['kitchen_repair']=runpy.run_path(str(kitchen_repair/'install_level.py'))['apply_upgrade'](world)
 traffic=PROJECT/'SourceAssets/CyberpunkTrafficUpgrade20261026'
 if (traffic/'installed.json').exists():
  import runpy
  result['traffic']=runpy.run_path(str(traffic/'install_level.py'))['apply_upgrade'](world)
 apartment_cables=PROJECT/'SourceAssets/CyberpunkApartmentCables20261027'
 if (apartment_cables/'installed.json').exists():
  import runpy
  result['apartment_cables']=runpy.run_path(str(apartment_cables/'install_level.py'))['apply_upgrade'](world)
 near_bank=PROJECT/'SourceAssets/CyberpunkNearBank20261028'
 if (near_bank/'installed.json').exists():
  import runpy
  result['near_bank']=runpy.run_path(str(near_bank/'install_level.py'))['apply_upgrade'](world)
 native_near_bank=PROJECT/'SourceAssets/NearBankPCGRepair20261028'
 if (native_near_bank/'installed.json').exists():
  import runpy
  result['native_near_bank']=runpy.run_path(str(native_near_bank/'install_level.py'))['apply_upgrade'](world)
 return result
def audit(world):
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)};report=dict(map=MAP,doors=[],containers=[],controls=[],atmosphere=[],furniture=[],balcony={},revision_actors={});issues=[]
 def fail(condition,reason):
  if not condition:issues.append(reason)
 ids=set()
 for label,a in actors.items():
  if isinstance(a,u.ColdSteelSlidingDoor):
   auto=a.get_editor_property('auto_close_seconds');report['doors'].append(dict(actor=label,auto_close=auto,replicates=a.get_editor_property('replicates')));fail(auto<=0,'Door autoclose: '+label)
   fail(a.get_editor_property('replicates'),'Door not replicated: '+label)
  if isinstance(a,u.ColdSteelSceneContainer):
   ident=a.get_editor_property('container_id');fail(bool(ident) and ident not in ids,'Container identity: '+label);ids.add(ident)
   row=dict(actor=label,id=ident,replicates=a.get_editor_property('replicates'),reclosable=a.actor_has_tag('ColdSteel.SceneContainer.Reclosable'),body=bool(a.body.static_mesh),moving_part=bool(a.door.static_mesh));report['containers'].append(row);fail(all(row[k] for k in ['replicates','reclosable','body','moving_part']),'Container setup: '+label)
  if isinstance(a,u.ApartmentDeviceControl):report['controls'].append(dict(actor=label,replicates=a.get_editor_property('replicates')));fail(a.get_editor_property('replicates'),'Control not replicated: '+label)
  if isinstance(a,u.ApartmentAtmosphere):
   lights=a.get_editor_property('lights');devices=a.get_editor_property('devices');rooms=a.get_editor_property('rooms');portals=a.get_editor_property('portals')
   row=dict(actor=label,lights=len(lights),devices=len(devices),rooms=len(rooms),portals=len(portals),clock=bool(a.get_editor_property('animation_clock')));report['atmosphere'].append(row);fail(row['clock'],'No material network clock')
   row['light_bindings']=[]
   for b in lights:
    light=b.get_editor_property('actor');fixtures=b.get_editor_property('fixtures');label=light.get_actor_label() if light else '<missing>'
    row['light_bindings'].append(dict(light=label,fixtures=[f.get_actor_label() if f else None for f in fixtures]))
    fail(bool(light) and bool(fixtures) and all(fixtures),'Missing light fixture binding: '+label)
   for b in devices:fail(bool(b.get_editor_property('station')) and bool(b.get_editor_property('control')),'Missing manual device binding')
 profiles=json.loads((PROJECT/'Content/ColdSteelData/apartment_furniture_rest.json').read_text())
 registered={r['mesh']:r for r in profiles['furniture']}
 for label in ['AP_Bed2_Bed','AP_Bed3_Bed','AP_Living_Sofa']:
  a=actors.get(label);fail(bool(a),'Missing furniture '+label)
  if not a:continue
  path=a.static_mesh_component.static_mesh.get_path_name();profile=registered.get(path);s=list(a.get_actor_scale3d().to_tuple());report['furniture'].append(dict(actor=label,mesh=path,scale=s,profile=bool(profile)))
  fail(bool(profile),'Furniture profile missing '+label)
  if profile:fail(all(abs(x-y)<.02 for x,y in zip(s,profile.get('scale',[1,1,1]))),'Furniture scale mismatch '+label)
 body=json.loads((PROJECT/'Content/ColdSteelData/player_body.json').read_text());clips=body.get('clips',{});report['rest_clips']={k:u.EditorAssetLibrary.does_asset_exist(v) for k,v in clips.items() if k.startswith('Rest.Apartment')}
 fail(len(report['rest_clips'])>=6 and all(report['rest_clips'].values()),'Apartment rest clips unresolved')
 for label in ['AP20_SideFrames','AP20_SideGlass','AP20_SideCollision']:
  a=actors.get(label);fail(bool(a),'Balcony missing '+label)
  if not a:continue
  c=a.static_mesh_component;report['balcony'][label]=dict(mesh=c.static_mesh.get_path_name(),convex=SM.get_convex_collision_count(c.static_mesh),collision=str(c.get_collision_enabled()),materials=[m.get_path_name() if m else None for m in c.get_materials()])
 fail('AP_BalconyPrivacy' not in actors,'Opaque balcony screen restored')
 if 'AP20_SideCollision' in report['balcony']:fail(report['balcony']['AP20_SideCollision']['convex']==2,'Side rail simple collision missing')
 for prefix in ['AP13_','AP15_','AP16_','AP18_','AP19_','AP20_']:report['revision_actors'][prefix]=sum(label.startswith(prefix) for label in actors)
 report['player_starts']=[dict(actor=a.get_actor_label(),p=list(a.get_actor_location().to_tuple())) for a in actors.values() if isinstance(a,u.PlayerStart)]
 report['issues']=issues;report['structural_pass']=not issues;report['rendered']=False;report['game_run']=False
 (R/'map-audit.json').write_text(json.dumps(report,indent=2),encoding='utf8');return report
def main():
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if editor and editor.get_game_world():raise RuntimeError('Preserve running game')
 if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
 backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
 world=u.EditorLoadingAndSavingUtils.load_map(MAP);assets=clock_assets(world);fixed=bind_existing_fixtures(world);report=audit(world)
 if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Network clock map save failed')
 (R/'installed.json').write_text(json.dumps(dict(stage='map_saved',saved_at=datetime.now().astimezone().isoformat(),backup=str(backup),clock_slots=len(assets['bindings']),fixture_bindings_added=fixed,structural_issues=report['issues']),indent=2),encoding='utf8');print('AP21_CLOCK_AND_MAP_SAVED',len(assets['bindings']),report['issues'])
if __name__=='__main__':main()
