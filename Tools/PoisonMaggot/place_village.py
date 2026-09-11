import unreal,json,hashlib,shutil
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME');out=root/'Saved/PoisonMaggot';level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
map_path='/Game/GameMaps/L_Normandy_FPS_Test';map_file=root/'Content/GameMaps/L_Normandy_FPS_Test.umap';backup=out/'L_Normandy_FPS_Test.before-maggot.umap'
if not backup.exists():shutil.copy2(map_file,backup)
before=hashlib.sha256(map_file.read_bytes()).hexdigest();assert level.load_level(map_path);world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();all_actors=actors.get_all_level_actors();starts=[a for a in all_actors if isinstance(a,unreal.PlayerStart)];assert len(starts)==1;start=starts[0]
bp=unreal.load_asset('/Game/Monsters/PoisonMaggot/BP_PoisonMaggot');assert bp;existing=[a for a in all_actors if isinstance(a,unreal.PoisonMaggotSpawner)];assert len(existing)<=1
if existing:spawner=existing[0];position=spawner.get_actor_location()
else:
 position=unreal.PoisonMaggotSpawner.find_village_spawn(world,start.get_actor_location(),start.get_actor_rotation());assert position is not None,'No supported open village location';spawner=actors.spawn_actor_from_class(unreal.PoisonMaggotSpawner,position)
spawner.set_actor_label('PoisonMaggot_Village_01');spawner.set_folder_path('Gameplay/Monsters/PoisonMaggot');spawner.set_editor_property('is_spatially_loaded',False);spawner.set_editor_property('monster_class',bp.generated_class());spawner.set_editor_property('respawn_seconds',300);spawner.set_editor_property('enabled',True)
spawner.set_actor_rotation(unreal.Rotator(yaw=unreal.MathLibrary.find_look_at_rotation(position,start.get_actor_location()).yaw),False)
# This new agent has no baked tiles in this commandlet. Preserve existing agents.
for a in actors.get_all_level_actors():
 if isinstance(a,unreal.RecastNavMesh) and 'PoisonMaggot' in a.get_name():actors.destroy_actor(a)
assert level.save_current_level();assert level.load_level(map_path);saved=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.PoisonMaggotSpawner)];assert len(saved)==1 and saved[0].get_editor_property('monster_class')
report={'map':map_path,'position':{'x':position.x,'y':position.y,'z':position.z},'label':'PoisonMaggot_Village_01','before_sha256':before,'backup':str(backup),'saved_readback':True,'respawn_after_corpse_removal_s':300}
(out/'village-placement.json').write_text(json.dumps(report,indent=2));unreal.log('MAGGOT_VILLAGE_SAVED '+json.dumps(report))
