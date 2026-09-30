import unreal as u,json
from pathlib import Path
targets=['/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10',
 '/Game/Weapons/LMG201/Production20260927/SM_LMG201_FrontSight',
 '/Game/Weapons/LMG201/Production20260927/SM_LMG201_RearSight']
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
d={'pie_active':u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is not None,
   'dirty_targets':[p for p in dirty if p in targets],
   'delete_api':u.GeometryScript_MeshEdits.delete_triangles_from_mesh.__doc__,
   'list_api':u.GeometryScript_List.convert_array_to_index_list.__doc__}
(Path(__file__).parent/'editor_state.json').write_text(json.dumps(d,indent=2))
print(json.dumps(d))
