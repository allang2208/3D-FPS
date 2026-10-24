"""Replace only the owned skyline and its city reflection; preserve V16 street life."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy,shutil
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));PROJECT=C['PROJECT'];MAP=C['MAP'];TAG='Apartment.V17.ArchitecturalNight'
def apply_upgrade(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong skyline target')
 assets=json.loads((R/'assets_saved.json').read_text());actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
 if assets['stage']!='assets_saved':raise RuntimeError('Finish architectural assets first')
 rows=[]
 for key,row in assets['meshes'].items():
  label='AP7_Bay'+key if key.startswith('Landmark_') else 'BAY_'+key
  a=actors[label];a.modify();c=a.static_mesh_component;c.set_static_mesh(u.load_asset(row['path']));c.set_editor_property('override_materials',[])
  a.set_actor_location(u.Vector(),False,False);a.set_actor_rotation(u.Rotator(),False);a.set_actor_scale3d(u.Vector(1,1,1));a.set_actor_enable_collision(False)
  tags=list(a.get_editor_property('tags'))
  if u.Name(TAG) not in tags:tags.append(u.Name(TAG));a.set_editor_property('tags',tags)
  c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False);c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('affect_distance_field_lighting',False)
  rows.append(dict(actor=label,mesh=row['path'],triangles=row['triangles']))
 # Port glazing and incidental skyline signs are also covered, not just towers.
 accents=[]
 for label,a in actors.items():
  if not (label.startswith(('BAY_','AP15_'))):continue
  for comp in a.get_components_by_class(u.StaticMeshComponent):
   if not comp.static_mesh:continue
   for i,slot in enumerate(comp.static_mesh.get_editor_property('static_materials')):
    role=str(slot.material_slot_name);path=None
    if label=='BAY_Harbor' and role in ['Office','Residential','Tech']:path=assets['materials']['CopperArcade']
    elif label=='BAY_Harbor' and role in ['Signs','WarmLight','Navigation','Neon0','Neon1','Neon2','Neon3']:path=assets['materials'][role]
    elif label.startswith(('BAY_Quay_','BAY_NearBank','AP15_')) and role in ['Neon0','Neon1','Neon2','Neon3','WarmLight']:path=assets['materials'][role]
    if path:a.modify();comp.set_material(i,u.load_asset(path));accents.append(dict(actor=label,slot=i,material=path))
 water=actors['BAY_Water'];water.modify();water.static_mesh_component.set_material(0,u.load_asset(assets['materials']['Water']))
 report=dict(skyline_actors=rows,accent_slots=accents,facade_families=C['FAMILIES'],buildings=271,landmarks=5,water_reflection_rebaked=True,window_brightness_animation=False,street_traffic_preserved=True,billboards_preserved=True,searchlights_preserved=True,weather_preserved=True,new_dynamic_lights=0,new_tick_actors=0,new_capture_actors=0)
 next_revision=R.parent/'RefinementV18'
 if (next_revision/'installed.json').exists():report['v18']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
 return report
def main():
 s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if s and s.get_game_world():raise RuntimeError('Preserve active play session')
 if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
 backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
 world=u.EditorLoadingAndSavingUtils.load_map(MAP);report=apply_upgrade(world)
 if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Architectural map save failed')
 report.update(stage='map_saved',saved_at=datetime.now().astimezone().isoformat(),backup=str(backup),game_tested=False,performance_measured=False)
 (R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('AP17_MAP_SAVED',len(report['skyline_actors']))
if __name__=='__main__':main()
