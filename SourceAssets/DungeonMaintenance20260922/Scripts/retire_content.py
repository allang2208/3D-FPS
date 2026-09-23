"""Complete a recoverable move for UE-loaded packages via the editor asset API."""
from pathlib import Path
import unreal as u,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
plan=json.loads((ROOT/'Config/retirement.json').read_text());archive=PROJECT/plan['archive']
backups=json.loads((archive/'content-archive.json').read_text(encoding='utf-8-sig'))
E=u.EditorAssetLibrary;UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world() or UE.get_editor_world().get_path_name().split('.')[0]!='/Game/GameMaps/L_Dungeon_Prototype':raise RuntimeError('Preserve editor context')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
for a in AA.get_all_level_actors():
    for c in a.get_components_by_class(u.StaticMeshComponent):
        if c.static_mesh and any(c.static_mesh.get_path_name().startswith(r+'/') for r in plan['ue_roots']):raise RuntimeError('Retire live reference before moving '+a.get_actor_label())
for entry in backups:
    p=Path(entry['archived'])
    if not p.is_file() or p.stat().st_size!=entry['bytes']:raise RuntimeError('Required archived package missing '+str(p))
record=dict(stage='retiring_archived_packages',archive=str(archive),operations=[],tests_run=False)
def write():(ROOT/'Receipts/content-retirement.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
old_map='/Game/Dungeons/AtmosphereV2/Archive/L_Dungeon_IndustrialV1'
if E.does_asset_exist(old_map):
    if not E.delete_asset(old_map):raise RuntimeError('Could not retire archived legacy map')
    record['operations'].append(old_map);write()
for root in plan['ue_roots']:
    if E.does_directory_exist(root):
        if not E.delete_directory(root):raise RuntimeError('Could not retire backed-up asset folder '+root)
    record['operations'].append(root);write()
record['stage']='content_archived_and_retired';write()
print('REJECTED_CONTENT_MOVED_TO_TRASH '+json.dumps(record))
