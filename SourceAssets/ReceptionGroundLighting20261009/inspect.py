"""Read the saved reception and existing lamp geometry; no gameplay or map switch."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parent
(ROOT/'Receipts').mkdir(exist_ok=True)
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=(u.EditorLoadingAndSavingUtils.load_map if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower() else u.load_asset)('/Game/GameMaps/L_Dungeon_Randomized')
g=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
c=json.loads(g.get_editor_property('module_catalog_json'))
m=next(m for m in c['modules'] if m['id']=='FacilityReceptionHall')
mesh=u.load_asset('/Game/Dungeons/IndustrialV1/Meshes/SM_CeilingLamp_Cool')
b=mesh.get_bounds()
report=dict(editor=ed.get_editor_world().get_path_name(),game=ed.get_game_world().get_path_name() if ed.get_game_world() else None,
    dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    dirty_content=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
    lights=m['lights'],postprocess=m.get('postprocess_lighting'),runtime_actors=m.get('runtime_actors'),
    mesh=dict(path=mesh.get_path_name(),origin=[b.origin.x,b.origin.y,b.origin.z],extent=[b.box_extent.x,b.box_extent.y,b.box_extent.z],
              materials=[s.material_interface.get_path_name() for s in mesh.static_materials]))
(ROOT/'Receipts/before.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ('lights','runtime_actors')},ensure_ascii=False))
