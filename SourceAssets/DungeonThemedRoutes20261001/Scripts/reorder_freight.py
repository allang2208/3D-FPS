"""Change only the freight route order in the existing saved production map."""
import hashlib,json,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
SEQUENCE=['FreightTransfer_WarehouseLink','AbandonedCargoWarehouse','AbandonedTransitStation']
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
if levels and levels.is_in_play_in_editor():raise RuntimeError('Preserve active PIE; save route order after play ends')
dirty={p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())}
if TARGET in dirty:raise RuntimeError('Preserve unsaved production map before changing route order')
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
world=u.EditorLoadingAndSavingUtils.load_map(TARGET) if commandlet else u.load_asset(TARGET)
if not world:raise RuntimeError('Production map unavailable')
# Inactive map packages have loaded actors but are not initialized gameplay worlds.
generators=[a for a in u.ObjectIterator(u.AuthoredDungeonGenerator) if a.get_path_name().startswith(TARGET+'.')]
if len(generators)!=1:raise RuntimeError('Production generator unavailable')
g=generators[0];before=g.get_editor_property('module_catalog_json');catalog=json.loads(before)
route=next(r for r in catalog['themed_routes']['routes'] if r['id']=='freight')
old=route['sequence'][:];route['sequence']=SEQUENCE
backup=ROOT/'Backup'/('catalog-before-reorder-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')
if not backup.exists():backup.write_text(before,encoding='utf-8')
source=PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap';digest=hashlib.sha256(source.read_bytes()).hexdigest()
saved_copy=ROOT/'Backup'/('L_Dungeon_Randomized-before-reorder-'+digest[:12]+'.umap')
if not saved_copy.exists():shutil.copy2(source,saved_copy)
with u.ScopedEditorTransaction('Reorder freight themed route'):
    g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
saved=u.EditorLoadingAndSavingUtils.save_map(world,TARGET) if commandlet else u.EditorLoadingAndSavingUtils.save_packages([world.get_outer()],False)
if not saved:raise RuntimeError('Route order not saved')
text=json.dumps(catalog,ensure_ascii=False,indent=2)
for path in (ROOT/'Config/catalog.json',PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json'):
    path.write_text(text,encoding='utf-8')
receipt=ROOT/'Receipts/install.json';data=json.loads(receipt.read_text('utf-8'))
data['routes']=catalog['themed_routes'];receipt.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Receipts/freight-reorder.json').write_text(json.dumps(dict(stage='map_saved',map=TARGET,
    before=old,after=SEQUENCE,tests_run=False,generation_executed=False,editor_started=False),indent=2),encoding='utf-8')
print('FREIGHT_ORDER_SAVED',json.dumps(SEQUENCE),flush=True)
