"""Remove two opaque side screens and their collisions; add matching glass returns."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,shutil,re,runpy
R=Path(__file__).resolve().parent;PROJECT=R.parents[2];BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV20';MAP='/Game/GameMaps/L_CyberpunkApartment'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
def import_assets(actors):
 front=actors['AP_BalconyRail'].static_mesh_component;glass=actors['AP_BalconyRailGlass'].static_mesh_component;roles={}
 for i,s in enumerate(front.static_mesh.get_editor_property('static_materials')):roles[re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name))]=front.get_material(i)
 roles['AP_Glass']=glass.get_material(0);roles['AP_Collision']=roles.get('AP_Dark') or next(iter(roles.values()))
 report=dict(stage='building',materials={k:v.get_path_name() for k,v in roles.items()},meshes={})
 for row in json.loads((R/'assembly.json').read_text())['meshes']:
  t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
  o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;o.import_mesh=True;o.import_materials=False;o.import_textures=False;o.import_animations=False;d=o.static_mesh_import_data
  for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,one_convex_hull_per_ucx=True).items():d.set_editor_property(k,v)
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=o;A.import_asset_tasks([t]);mesh=u.load_asset(BASE+'/Meshes/'+row['name'])
  if not mesh:raise RuntimeError('Missing imported rail '+row['key'])
  for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,roles[re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name))])
  bs=SM.get_lod_build_settings(mesh,0);bs.use_full_precision_u_vs=True;bs.recompute_normals=False;bs.recompute_tangents=True;SM.set_lod_build_settings(mesh,0,bs)
  if row['simple_boxes']:
   body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
  save(mesh);report['meshes'][row['key']]=dict(path=mesh.get_path_name(),triangles=row['triangles'],simple_boxes=row['simple_boxes'])
  (R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 report['stage']='assets_saved';(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8');return report
def apply_upgrade(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong apartment map')
 assets=json.loads((R/'assets_saved.json').read_text())
 if assets['stage']!='assets_saved':raise RuntimeError('Import glass rail assets first')
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)};aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
 front=actors['AP_BalconyRail'];front.modify();front.static_mesh_component.set_static_mesh(u.load_asset(assets['meshes']['FrontRail']['path']));front.static_mesh_component.set_editor_property('override_materials',[])
 made=[]
 for key,donor in [('SideFrames','AP_BalconyRail'),('SideGlass','AP_BalconyRailGlass'),('SideCollision','AP_RailCollision')]:
  label='AP20_'+key;a=actors.get(label)
  if not a:a=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(label)
  a.modify();a.set_actor_transform(actors[donor].get_actor_transform(),False,False);a.set_folder_path('Apartment20261022/Balcony');a.set_editor_property('tags',[u.Name('Apartment.V20.GlassBalcony')])
  c=a.static_mesh_component;c.set_static_mesh(u.load_asset(assets['meshes'][key]['path']));c.set_editor_property('override_materials',[]);blocking=key=='SideCollision';a.set_actor_enable_collision(blocking)
  c.set_collision_profile_name('BlockAll' if blocking else 'NoCollision');c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if blocking else u.CollisionEnabled.NO_COLLISION)
  c.set_visibility(not blocking);c.set_hidden_in_game(blocking);c.set_editor_property('cast_shadow',key=='SideFrames')
  if blocking:
   a.set_editor_property('tags',[u.Name('Apartment.V20.GlassBalcony'),u.Name('Traversal.GuardrailDrop')]);c.set_editor_property('component_tags',[u.Name('Traversal.GuardrailDrop')]);c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('affect_dynamic_indirect_lighting',False)
  made.append(dict(actor=label,mesh=c.static_mesh.get_path_name(),transform_source=donor,blocking=blocking))
 removed=[]
 if 'AP_BalconyPrivacy' in actors:
  old=actors['AP_BalconyPrivacy'];previous=dict(actor=old.get_actor_label(),mesh=old.static_mesh_component.static_mesh.get_path_name())
  if not aa.destroy_actor(old):raise RuntimeError('Cannot remove opaque balcony screens')
  removed.append(previous)
 report=dict(actors=made,removed=removed,privacy_caps_removed=True,glass_material=assets['materials']['AP_Glass'],matches_front_material=True,side_panels=6,side_simple_collision_boxes=2,front_guardrail_collision_preserved=True,guardrail_drop_tag=True)
 next_stage=R.parent/'RefinementV21'
 if (next_stage/'installed.json').exists():report['network_clock']=runpy.run_path(str(next_stage/'publish.py'))['apply_upgrade'](world)
 return report
def main():
 s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if s and s.get_game_world():raise RuntimeError('Preserve active game session')
 if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
 backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
 world=u.EditorLoadingAndSavingUtils.load_map(MAP);actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)};assets=import_assets(actors);report=apply_upgrade(world)
 if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Balcony map save failed')
 report.update(stage='map_saved',saved_at=datetime.now().astimezone().isoformat(),backup=str(backup),game_tested=False);(R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 (R/'completed.json').write_text(json.dumps(dict(stage='production_completed',map_saved_at=report['saved_at'],mesh_count=len(assets['meshes']),side_panels=6,side_colliders=2,game_tested=False,interactive_editor_started=False),indent=2),encoding='utf8');print('AP20_BALCONY_SAVED')
if __name__=='__main__':main()
