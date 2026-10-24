from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy,shutil,traceback
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));BASE=C['BASE'];MAP=C['MAP'];PROJECT=C['PROJECT']
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
def apply_upgrade(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong AP10 target map')
 assets=json.loads((R/'assets_saved.json').read_text())
 if assets['stage']!='assets_saved':raise RuntimeError('AP10 assets not saved')
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
 water=actors.get('BAY_Water')
 if not water:raise RuntimeError('Existing apartment bay water missing')
 placements=[]
 def place(label,mesh,p,scale,material=None):
  a=actors.get(label)
  if not a:a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*p));a.set_actor_label(label)
  a.modify();a.set_folder_path('Apartment20261022/BayAdvertisingFrontRow')
  tags=list(a.get_editor_property('tags'))
  if u.Name('CyberpunkApartment.RefinementV10') not in tags:tags.append(u.Name('CyberpunkApartment.RefinementV10'));a.set_editor_property('tags',tags)
  comp=a.static_mesh_component;comp.set_static_mesh(u.load_asset(mesh));comp.set_editor_property('override_materials',[]);comp.set_collision_profile_name('NoCollision');comp.set_editor_property('cast_shadow',False);comp.set_editor_property('affect_distance_field_lighting',False)
  if material:comp.set_material(0,u.load_asset(material))
  a.set_actor_location(u.Vector(*p),False,False);a.set_actor_rotation(u.Rotator(),False);a.set_actor_scale3d(u.Vector(*scale))
  placements.append(dict(actor=label,location_cm=p,scale=scale));return a
 place('AP8_BillboardStructures',assets['meshes']['frames'],(0,0,0),(1.25,1.25,1.25))
 for b in C['BOARDS']:
  p=tuple(x*100 for x in C['world_metres'](b['p']))
  place('AP8_Advertisement_'+b['key'],C['OLD8']+'/Meshes/SM_AP8_Display',p,(b['w']*1.25,1.25,b['h']*1.25),assets['materials']['MI_AP10_'+b['key']])
 water.modify();water.static_mesh_component.set_material(0,u.load_asset(assets['water']['path']))
 report=dict(placements=placements,board_layout=C['BOARDS'],water=assets['water'],preserved_searchlight_actors=[k for k in actors if k.startswith('AP9_')],removed_duplicate_screens=0,ad_screen_count=6,new_scene_captures=0,new_tick_actors=0,new_textures=0)
 next_revision=R.parent/'RefinementV11'
 if (next_revision/'installed.json').exists():report['v11']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
 return report
def main():
 report=dict(stage='preparing',map=MAP,game_run=False,visual_acceptance=False,performance_measured=False)
 try:
  if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps before AP10 publication')
  backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
  s=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=s.get_editor_world() if s else None
  if not world or world.get_path_name().split('.')[0]!=MAP:world=u.EditorLoadingAndSavingUtils.load_map(MAP)
  report.update(apply_upgrade(world))
  if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('AP10 map save failed')
  report['stage']='map_saved';report['backup']=str(backup);report['saved_at']=datetime.now().astimezone().isoformat();(R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();raise
 finally:(R/'map_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if __name__=='__main__':main()
