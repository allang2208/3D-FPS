from pathlib import Path
import json
import unreal as u
root=Path(__file__).resolve().parent
result={}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
result['pie_active']=bool(editor and editor.get_game_world())
for name,path in [('m10','/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler'),('m25','/Game/Monsters/VortexCofferM25/BP_VortexCofferM25')]:
    bp=u.load_asset(path)
    if bp is None:raise RuntimeError('Missing '+path)
    actor=u.get_default_object(bp.generated_class())
    move=actor.get_editor_property('character_movement')
    data={key:actor.get_editor_property(key) for key in ['walk_speed','animation_walk_speed']}
    if name=='m10':data.update({key:actor.get_editor_property(key) for key in ['moving_turn_speed','pivot_turn_speed','turn_acceleration']})
    data['movement']={key:move.get_editor_property(key) for key in ['max_walk_speed','max_acceleration','braking_deceleration_walking']}
    data['movement']['rotation_rate_yaw']=move.get_editor_property('rotation_rate').yaw
    result[name]=data
result['dirty_m25_packages']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith('/Game/Monsters/VortexCofferM25')]
(root/'reference_settings.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('M25_MOVEMENT_REFERENCE '+json.dumps(result))
