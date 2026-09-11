"""Install owned BT/controller/hit assets, navigation and an isolated obstacle course."""
import unreal,json,shutil
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/Saved/MonsterAI');out.mkdir(exist_ok=True)
lib=unreal.EditorAssetLibrary;tools=unreal.AssetToolsHelpers.get_asset_tools();dest='/Game/Monsters/AI'
tree=unreal.load_asset(dest+'/BT_Monster')
if not tree:tree=tools.create_asset('BT_Monster',dest,unreal.BehaviorTree,unreal.BehaviorTreeFactory())
assert unreal.MonsterAIController.build_tree(tree);assert lib.save_loaded_asset(tree,False)
path=dest+'/BP_MonsterAIController';bp=unreal.load_asset(path)
if not bp:
 f=unreal.BlueprintFactory();f.set_editor_property('parent_class',unreal.MonsterAIController);bp=tools.create_asset('BP_MonsterAIController',dest,unreal.Blueprint,f)
unreal.BlueprintEditorLibrary.compile_blueprint(bp);controller=bp.generated_class();unreal.get_default_object(controller).set_editor_property('behavior',tree);lib.save_loaded_asset(bp,False)
clips={};classes={}
for kind,path in [('Nurse','/Game/Monsters/NurseZombie/BP_NurseZombie'),('HandBrain','/Game/Monsters/HandBrain/BP_HandBrain')]:
 actorbp=unreal.load_asset(path);unreal.BlueprintEditorLibrary.compile_blueprint(actorbp);cdo=unreal.get_default_object(actorbp.generated_class())
 hitpath=dest+'/A_'+kind+'_Hit';hit=unreal.load_asset(hitpath)
 if not hit:hit=lib.duplicate_asset(cdo.get_editor_property('idle_clip').get_path_name().split('.')[0],hitpath)
 assert unreal.MonsterCombatComponent.author_hit_clip(hit,kind=='HandBrain');lib.save_loaded_asset(hit,False);clips[kind]=hit
 cdo.set_editor_property('ai_controller_class',controller);cdo.set_editor_property('auto_possess_ai',unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
 cdo.get_editor_property('combat').set_editor_property('hit_clip',hit)
 lib.save_loaded_asset(actorbp,False);classes[kind]=actorbp.generated_class()
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mapname='/Game/GameMaps/L_Normandy_FPS_Test';file=Path('D:/FPS3D/FPSGAME/Content/GameMaps/L_Normandy_FPS_Test.umap')
backup=out/'L_Normandy_FPS_Test.before-ai.umap'
if not backup.exists():shutil.copy2(file,backup)
assert level.load_level(mapname)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();points=[]
for a in actors.get_all_level_actors():
 if isinstance(a,(unreal.NurseZombie,unreal.HandBrainMonster)):
  kind='Nurse' if isinstance(a,unreal.NurseZombie) else 'HandBrain'
  a.set_editor_property('ai_controller_class',controller);a.set_editor_property('auto_possess_ai',unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED);a.get_editor_property('combat').set_editor_property('hit_clip',clips[kind]);points.append(a.get_actor_location())
 if isinstance(a,(unreal.PlayerStart,unreal.HandBrainVillageSpawner)):points.append(a.get_actor_location())
assert points
center=unreal.Vector(sum(p.x for p in points)/len(points),sum(p.y for p in points)/len(points),sum(p.z for p in points)/len(points))
assert unreal.MonsterAIController.build_navigation_bounds(world,center,unreal.Vector(6500,6500,2000));assert level.save_current_level()
# Separate map: wall blocks direct chase; either end is navigable.
test='/Game/Tests/MonsterAI/L_MonsterAI';assert level.new_level(test)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
cube=unreal.load_asset('/Engine/BasicShapes/Cube');mat=unreal.load_asset('/Engine/BasicShapes/BasicShapeMaterial')
def box(name,location,scale):
 a=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*location));a.set_actor_label(name);a.static_mesh_component.set_static_mesh(cube);a.static_mesh_component.set_material(0,mat);a.set_actor_scale3d(unreal.Vector(*scale));a.static_mesh_component.set_collision_profile_name('BlockAll');return a
box('AuditFloor',(0,0,-50),(36,30,1));box('AuditWall',(0,0,180),(1.2,8,3.6))
start=actors.spawn_actor_from_class(unreal.PlayerStart,unreal.Vector(700,0,100));start.set_actor_rotation(unreal.Rotator(yaw=180),False)
nurse=actors.spawn_actor_from_class(classes['Nurse'],unreal.Vector(-700,0,100));nurse.set_actor_label('AI_Audit_Nurse');nurse.set_actor_rotation(unreal.Rotator(yaw=0),False);nurse.set_editor_property('max_health',1000);nurse.set_editor_property('walk_speed',250);nurse.set_editor_property('aggro_radius',1800)
nurse.set_editor_property('ai_controller_class',controller);nurse.set_editor_property('auto_possess_ai',unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
sun=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,800),unreal.Rotator(pitch=-50,yaw=-35));sun.light_component.set_editor_property('intensity',4)
actors.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,500))
assert unreal.MonsterAIController.build_navigation_bounds(world,unreal.Vector(0,0,250),unreal.Vector(1800,1500,600));assert level.save_current_level()
(out/'installation.json').write_text(json.dumps({'tree':tree.get_path_name(),'controller':controller.get_path_name(),'hit_clips':{k:v.get_path_name() for k,v in clips.items()},'village_navigation_center':str(center),'test_map':test},indent=2))
unreal.log('MONSTER_AI_INSTALLED')
