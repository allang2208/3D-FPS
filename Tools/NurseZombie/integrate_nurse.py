"""Create owned clips/Blueprint and place two test enemies; preserves downloaded assets."""
import unreal,json,shutil,math
from pathlib import Path
out=Path(unreal.Paths.project_saved_dir())/'NurseZombie'
out.mkdir(parents=True,exist_ok=True)
source='/Game/ZombieFemale/Asset/'
dest='/Game/Monsters/NurseZombie/'
mesh=unreal.load_asset(source+'Meshes/ZombieFemale_NurseOutfit')
clips={}
for key,name in [('idle','Idle05'),('walk','Walk01Forward'),('attack','AttackForward05')]:
    path=dest+'A_Nurse_'+key
    clip=unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else unreal.EditorAssetLibrary.duplicate_asset(source+'Animations/ANMS_ZombieFemale'+name,path)
    assert clip
    if key!='idle': assert unreal.NurseZombie.prepare_in_place_animation(clip)
    clip.set_preview_skeletal_mesh(mesh)
    unreal.EditorAssetLibrary.save_loaded_asset(clip)
    clips[key]=clip
bp_path=dest+'BP_NurseZombie'
if unreal.EditorAssetLibrary.does_asset_exist(bp_path):
    bp=unreal.load_asset(bp_path)
else:
    factory=unreal.BlueprintFactory()
    factory.set_editor_property('parent_class',unreal.NurseZombie)
    bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_NurseZombie',dest.rstrip('/'),unreal.Blueprint,factory)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=unreal.get_default_object(bp.generated_class())
cdo.set_editor_property('visual_mesh',mesh)
cdo.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
for key,clip in clips.items(): cdo.set_editor_property(key+'_clip',clip)
cdo.set_editor_property('walk_speed',52.0)
unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
map_path='/Game/GameMaps/L_Normandy_FPS_Test'
map_file=Path(unreal.Paths.project_content_dir())/'GameMaps/L_Normandy_FPS_Test.umap'
backup=out/'L_Normandy_FPS_Test.before-nurse.umap'
if not backup.exists(): shutil.copy2(map_file,backup)
assert level.load_level(map_path)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
starts=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.PlayerStart)]
assert len(starts)==1
start=starts[0]
# Source map's imported PlayerStart is tilted almost upside down, putting the FPS eye below its feet.
# Keep its horizontal heading; character capsules must spawn upright.
initial_forward=start.get_actor_forward_vector()
heading=math.degrees(math.atan2(initial_forward.y,initial_forward.x))
start.set_actor_rotation(unreal.Rotator(pitch=0,yaw=heading,roll=0),False)
origin=start.get_actor_location();forward=start.get_actor_forward_vector();right=start.get_actor_right_vector()
existing=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.NurseZombie)]
report=[]
for index,(distance,side) in enumerate([(350,120),(650,-180)]):
    near=origin+forward*distance+right*side
    safe=unreal.NurseZombie.find_test_spawn(world,origin,start.get_actor_rotation(),distance,side)
    assert safe is not None
    label='NurseZombie_Test_'+str(index+1)
    actor=next((a for a in existing if a.get_actor_label()==label),None)
    if actor is None: actor=actors.spawn_actor_from_class(bp.generated_class(),safe)
    actor.set_actor_location(safe,False,False)
    actor.set_actor_rotation(unreal.Rotator(pitch=0,yaw=unreal.MathLibrary.find_look_at_rotation(safe,origin).yaw,roll=0),False)
    actor.set_actor_label(label)
    actor.set_editor_property('is_spatially_loaded',False)
    actor.set_folder_path('Gameplay/NurseZombieTests')
    actor.set_editor_property('aggro_radius',850.0)
    actor.set_editor_property('visual_mesh',mesh)
    actor.mesh.set_skeletal_mesh_asset(mesh)
    for key,clip in clips.items(): actor.set_editor_property(key+'_clip',clip)
    actor.set_editor_property('walk_speed',52.0)
    report.append({'label':label,'location':str(safe),'mesh':str(actor.mesh.skeletal_mesh_asset)})
assert level.save_current_level()
assert level.load_level(map_path)
loaded=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.NurseZombie)]
assert len(loaded)==2
for a in loaded:
    unreal.log('NURSE_RELOAD '+str([(k,str(a.get_editor_property(k))) for k in ['idle_clip','walk_clip','attack_clip','visual_mesh']]))
    assert a.get_editor_property('idle_clip') is not None and a.get_editor_property('walk_clip') is not None and a.get_editor_property('attack_clip') is not None
(out/'integration.json').write_text(json.dumps({'map':map_path,'blueprint':bp_path,'actors':report,'reloaded':len(loaded)},indent=2),encoding='utf-8')
unreal.log('NURSE_INTEGRATION_OK '+json.dumps(report))
