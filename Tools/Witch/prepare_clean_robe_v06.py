"""Read the target authoring state before V06 import. No game test."""
import unreal as u,json
from pathlib import Path
mesh=u.load_asset('/Game/Monsters/WitchMeshy/OriginalRobeV05/SK_Witch_Meshy')
dirty=u.EditorLoadingAndSavingUtils.get_dirty_content_packages()+u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
report={'mesh':mesh.get_path_name(),'target_package_dirty':any(p.get_path_name()==mesh.get_path_name().split('.')[0] for p in dirty),
        'pie_running':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world())}
Path('D:/FPS3D/FPSGAME/Saved/WitchV06-import-state.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
