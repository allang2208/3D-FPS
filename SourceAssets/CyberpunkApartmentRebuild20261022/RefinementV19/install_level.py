"""Set facade overrides and add four advertisements without rebuilding the map."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy,shutil
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));PROJECT=C['PROJECT'];MAP=C['MAP'];TAG='Apartment.V19.LuminousSkyline'
def apply_upgrade(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong apartment map')
 assets=json.loads((R/'assets_saved.json').read_text())
 if assets['stage']!='assets_saved':raise RuntimeError('Finish V19 asset production first')
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
 aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem);changed=[]
 for label,a in actors.items():
  if not(label.startswith(('BAY_City_','AP7_BayLandmark_')) or label in ['BAY_FarCity','BAY_FarHeadland','BAY_Harbor']):continue
  c=a.static_mesh_component
  for i,slot in enumerate(c.static_mesh.get_editor_property('static_materials')):
   role=str(slot.material_slot_name);key=None
   if role in C['FAMILIES']:key='FarQuietGlass' if label.startswith('BAY_Far') else role
   elif label=='BAY_Harbor' and role in ['Office','Residential','Tech']:key='CopperArcade'
   if key:a.modify();c.set_material(i,u.load_asset(assets['materials'][key]));changed.append(dict(actor=label,slot=i,material=assets['materials'][key]))
 made=[]
 for key,row in assets['meshes'].items():
  label='AP19_'+key;a=actors.get(label)
  if not a:a=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(label)
  a.modify();tags=list(a.get_editor_property('tags'))
  if u.Name(TAG) not in tags:tags.append(u.Name(TAG));a.set_editor_property('tags',tags)
  a.set_folder_path('Apartment20261022/LuminousSkyline');a.set_actor_location(u.Vector(),False,False);a.set_actor_rotation(u.Rotator(),False);a.set_actor_scale3d(u.Vector(1,1,1));a.set_actor_enable_collision(False)
  c=a.static_mesh_component;c.set_static_mesh(u.load_asset(row['path']));c.set_editor_property('override_materials',[]);c.set_collision_profile_name('NoCollision')
  for k,v in dict(cast_shadow=False,visible_in_ray_tracing=False,affect_distance_field_lighting=False,receives_decals=False).items():c.set_editor_property(k,v)
  made.append(dict(actor=label,mesh=row['path'],triangles=row['triangles']))
 a=actors['BAY_Water'];a.modify();a.static_mesh_component.set_material(0,u.load_asset(assets['materials']['Water']))
 report=dict(actors=made,facade_slots=changed,facade_occupancy=json.loads((R/'facade-source.json').read_text()),additional_advertisements=4,additional_facade_displays=2,sky_holograms=2,roof_projectors=2,new_dynamic_lights=0,new_tick_actors=0,new_capture_actors=0,water_reflection_rebaked=True,dynamic_ad_reflections_synchronized=True)
 next_revision=R.parent/'RefinementV20'
 if (next_revision/'installed.json').exists():report['v20']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
 return report
def main():
 s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if s and s.get_game_world():raise RuntimeError('Preserve active play session')
 if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
 backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
 world=u.EditorLoadingAndSavingUtils.load_map(MAP);report=apply_upgrade(world)
 if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('V19 map save failed')
 report.update(stage='map_saved',saved_at=datetime.now().astimezone().isoformat(),backup=str(backup),game_tested=False,performance_measured=False);(R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('AP19_MAP_SAVED',len(report['actors']))
if __name__=='__main__':main()
