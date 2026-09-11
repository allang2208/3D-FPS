import unreal,json,shutil
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME');out=root/'Saved/HandBrain';level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
map_path='/Game/GameMaps/L_Normandy_FPS_Test';map_file=root/'Content/GameMaps/L_Normandy_FPS_Test.umap';backup=out/'L_Normandy_FPS_Test.before-handbrain.umap'
if not backup.exists():shutil.copy2(map_file,backup)
assert level.load_level(map_path)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();all_actors=actors.get_all_level_actors();starts=[a for a in all_actors if isinstance(a,unreal.PlayerStart)];assert len(starts)==1
start=starts[0];start_location=str(start.get_actor_location());bp=unreal.load_asset('/Game/Monsters/HandBrain/BP_HandBrain');assert bp
existing=[a for a in all_actors if isinstance(a,unreal.HandBrainVillageSpawner) and a.get_actor_label()=='HandBrain_Village_01'];assert len(existing)<=1
if existing:spawner=existing[0];position=spawner.get_actor_location()
else:
 position=unreal.HandBrainMonster.find_village_spawn(world,start.get_actor_location(),start.get_actor_rotation());assert position is not None,'No safe village spawn position'
 spawner=actors.spawn_actor_from_class(unreal.HandBrainVillageSpawner,position);assert spawner
spawner.set_actor_label('HandBrain_Village_01');spawner.set_folder_path('Gameplay/Monsters/HandBrain');spawner.set_editor_property('is_spatially_loaded',False)
spawner.set_editor_property('monster_class',bp.generated_class());spawner.set_editor_property('respawn_seconds',300.0);spawner.set_editor_property('enabled',True)
spawner.set_actor_rotation(unreal.Rotator(pitch=0,yaw=unreal.MathLibrary.find_look_at_rotation(position,start.get_actor_location()).yaw,roll=0),False)
assert level.save_current_level();assert level.load_level(map_path)
saved=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.HandBrainVillageSpawner) and a.get_actor_label()=='HandBrain_Village_01'];assert len(saved)==1 and saved[0].get_editor_property('monster_class')
result={'map':map_path,'label':'HandBrain_Village_01','position':{'x':position.x,'y':position.y,'z':position.z},'blueprint':bp.get_path_name(),'respawn_after_corpse_removal_seconds':300,'saved_readback':True,'player_start':start_location}
(out/'village-placement.json').write_text(json.dumps(result,indent=2));unreal.log('HANDBRAIN_VILLAGE_SAVED '+json.dumps(result))
