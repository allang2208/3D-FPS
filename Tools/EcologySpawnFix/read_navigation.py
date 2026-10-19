"""Read saved navigation/monster settings; no generation, monster spawning or gameplay."""
import unreal as u,json
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/EcologySpawnFix20261017')
def prop(obj,name):
 try:return obj.get_editor_property(name)
 except:return None
def scalar(v):
 if v is None or isinstance(v,(bool,int,float,str)):return v
 if isinstance(v,u.Object):return v.get_path_name()
 return str(v)
def mask(obj):return [bool(prop(obj,'supports_agent'+str(i))) for i in range(7)]
def agents(obj):
 return [{k:scalar(prop(a,k)) for k in ['name','agent_radius','agent_height','nav_data_class']} for a in prop(obj,'supported_agents')]
report={'navigation_defaults':agents(u.get_default_object(u.NavigationSystemV1)),'characters':{}}
for key,path in [('spiral','/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14'),('crown','/Game/Monsters/RootCrown/BP_RootCrownRigPreview')]:
 bp=u.load_asset(path);cdo=u.get_default_object(bp.generated_class());cap=cdo.get_editor_property('capsule_component');move=cdo.get_editor_property('character_movement');nav=prop(move,'nav_agent_props');policy=prop(move,'nav_movement_properties')
 report['characters'][key]={'blueprint':path,'capsule_radius':cap.get_scaled_capsule_radius(),'capsule_half_height':cap.get_scaled_capsule_half_height(),'agent':{k:scalar(prop(nav,k)) for k in ['agent_radius','agent_height','preferred_nav_data']},'update_nav_from_collision':scalar(prop(policy,'update_nav_agent_with_owners_collision'))}
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_Dungeon_Randomized')
nav=u.NavigationSystemV1.get_navigation_system(world)
report['world']=world.get_path_name();report['navigation_system']={'agents':agents(nav),'mask':mask(prop(nav,'supported_agents_mask'))}
report['bounds']=[];report['data']=[]
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.NavigationData):
 report['data'].append({'path':actor.get_path_name(),'label':actor.get_actor_label(),'class':actor.get_class().get_name(),**{k:scalar(prop(actor,k)) for k in ['agent_radius','agent_height','runtime_generation','force_rebuild_on_load','tile_pool_size','fixed_tile_pool_size','can_be_main_nav_data']}})
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.NavMeshBoundsVolume):
 report['bounds'].append({'path':actor.get_path_name(),'label':actor.get_actor_label(),'tags':[str(t) for t in actor.tags],'mask':mask(prop(actor,'supported_agents'))})
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator):
 data=prop(actor,'module_catalog_json')
 if data:
  catalog=json.loads(data);(OUT/'saved_catalog.json').write_text(data,encoding='utf-8');report['catalog_file']='saved_catalog.json'
(OUT/'navigation_inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('ECOLOGY_NAVIGATION_INPUTS_SAVED',json.dumps(report,ensure_ascii=False),flush=True)
