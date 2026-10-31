from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent;ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);game=ed.get_game_world();view=dict(source='balcony_authoring_anchor',eye_metres=[0,15,1.7])
if game and 'L_CyberpunkApartment' in game.get_path_name():
    camera=u.GameplayStatics.get_player_camera_manager(game,0)
    if camera:view=dict(source='current_apartment_player_camera',eye_metres=[v/100 for v in camera.get_camera_location().to_tuple()],rotation=list(camera.get_camera_rotation().to_tuple()),fov=camera.get_fov_angle())
view.update(game_world=game.get_path_name() if game else None,editor_world=ed.get_editor_world().get_path_name() if ed.get_editor_world() else None,dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(R/'riverfront_view.json').write_text(json.dumps(view,indent=2),encoding='utf8');print('RIVERFRONT_AUTHORING_VIEW',view,flush=True)
