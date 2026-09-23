"""Enable the imported terminal and its encounter, preserving the live room catalogue."""
import json,runpy
from pathlib import Path
import unreal as u
root=Path(__file__).resolve().parents[1]
if not u.load_class(None,'/Script/FPSGAME.DungeonBossEncounter'):
    raise RuntimeError('Native DungeonBossEncounter must be compiled and loaded before saving the map')
runpy.run_path(str(root.parent/'DungeonRouteRepairs20260922/Scripts/install.py'),run_name='__main__')
g=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label()=='DGN_RouteGenerator')
catalog=json.loads(g.get_editor_property('module_catalog_json'))
graph=json.loads(g.get_editor_property('layout_manifest_json'))
result=dict(stage='map_saved',map='/Game/GameMaps/L_Dungeon_Randomized',
    boss_terminal_enabled=catalog['boss_terminal_enabled'],boss_rooms=graph['boss_rooms'],
    boss_class=next(m['boss_encounter']['class'] for m in catalog['modules'] if m['id']=='BossPumpHall'),
    description=g.get_editor_property('layout_description'),tests_run=False)
(root/'Receipts/install.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'Receipts/installed-layout.json').write_text(g.get_editor_property('layout_manifest_json'),encoding='utf-8')
terminal=root.parent/'DungeonBossHall20260922/Config/terminal-modules.json'
data=json.loads(terminal.read_text(encoding='utf-8'))
data.update(status='imported_and_connected',runtime_routing_connected=True,integration_receipt='../DungeonBossIntegration20260923/Receipts/install.json')
terminal.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('BOSS_TERMINAL_INSTALLED',json.dumps(result,ensure_ascii=False))
