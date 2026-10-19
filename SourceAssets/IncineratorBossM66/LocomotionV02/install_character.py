"""Save the M66 navigation character after its native classes have a normal DLL."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/LocomotionV02')
E=u.EditorAssetLibrary;DEST='/Game/Monsters/IncineratorBossM66'
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before updating the M66 Blueprint')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 packages have unsaved changes')
mesh=u.load_asset(DEST+'/RigV01/SK_M66_BackCompleted');bp=u.load_asset(DEST+'/BP_M66RigPreview')
if not mesh or not bp:raise RuntimeError('M66 V01 mesh/Blueprint missing')
motion=json.loads((ROOT/'Records/motion_import.json').read_text(encoding='utf-8'))
clips={role:u.load_asset(path) for role,path in motion['clips'].items()}
if not all(clips.values()) or len(clips)!=4:raise RuntimeError('Four saved M66 clips are required')
u.BlueprintEditorLibrary.reparent_blueprint(bp,u.M66IncineratorMonster)
u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class())
for key,value in {'visual_mesh':mesh,'idle_clip':clips['Idle'],'move_clip':clips['Move'],
    'turn_left_clip':clips['TurnLeft'],'turn_right_clip':clips['TurnRight'],
    'walk_speed':80.,'return_speed':65.,'turn_speed':50.,'stride_distance':144.,'turn_stride_degrees':60.,
    'aggro_radius':2200.,'leash_radius':3200.,'stopping_distance':270.,
    'replicates':True,'replicate_movement':True,'can_be_damaged':False,
    'auto_possess_ai':u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED,
    'ai_controller_class':u.load_class(None,'/Game/Monsters/AI/BP_MonsterAIController.BP_MonsterAIController_C'),
    'tags':[u.Name('Enemy'),u.Name('M66'),u.Name('LocomotionStage')]}.items():cdo.set_editor_property(key,value)
capsule=cdo.get_editor_property('capsule_component');capsule.set_capsule_size(100.,190.,False)
move=cdo.get_editor_property('character_movement')
if not isinstance(move,u.M66MovementComponent):raise RuntimeError('Blueprint retained the old movement component')
move.set_editor_property('max_walk_speed',80.);move.set_editor_property('max_acceleration',140.)
move.set_editor_property('braking_deceleration_walking',220.)
move.set_editor_property('max_step_height',40.);move.set_editor_property('can_walk_off_ledges',False)
move.set_editor_property('orient_rotation_to_movement',False);move.set_editor_property('use_controller_desired_rotation',False)
nav=move.get_editor_property('nav_agent_props');nav.agent_radius=225.;nav.agent_height=450.;nav.agent_step_height=40.
move.set_editor_property('nav_agent_props',nav)
component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh)
component.set_anim_instance_class(u.M66AnimInstance.static_class())
component.set_editor_property('relative_rotation',u.Rotator(0.,0.,0.))
component.set_editor_property('relative_location',u.Vector(0.,0.,-190.))
component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
E.set_metadata_tag(bp,'M66.Stage','Idle, walk, left/right pivot and shared navigation; attacks/encounter not yet authored')
E.set_metadata_tag(bp,'M66.Navigation','Existing M10Mawcrawler agent: radius 225 cm, height 450 cm, step 40 cm')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 character save failed')
bounds=mesh.get_imported_bounds()
report={'saved':[bp.get_path_name()],'parent':cdo.get_class().get_super_class().get_name() if hasattr(cdo.get_class(),'get_super_class') else 'M66IncineratorMonster',
    'movement_class':move.get_class().get_name(),'animation_class':'M66AnimInstance','clips':motion['clips'],
    'nav_radius_cm':225,'nav_height_cm':450,'step_cm':40,'capsule_radius_cm':100,'capsule_half_height_cm':190,
    'source_stride_cm':144,'walk_speed_cm_s':80,'return_speed_cm_s':65,'turn_deg_s':50,
    'mesh_imported_height_cm':bounds.box_extent.z*2,'f6':'焚骸 M-35（待机·移动）',
    'server_authoritative_navigation':True,'runtime_tested':False,'complete':True}
(ROOT/'Records/character_install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M66_CHARACTER_SAVED '+json.dumps(report,ensure_ascii=False))
