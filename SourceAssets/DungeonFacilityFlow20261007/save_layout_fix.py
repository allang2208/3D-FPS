"""Save the circular-room seam correction without rebuilding the map preview."""
from pathlib import Path
import unreal as u
import json, hashlib, shutil, traceback, runpy

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
REVISION=runpy.run_path(str(ROOT/'extend_catalog.py'))['REVISION']
report=dict(stage='preparing',map=TARGET,revision=REVISION,tests_run=False,game_run=False,generated=False)
def record():
    (ROOT/'Receipts/layout-fix-save.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE; save stopped before writing')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
previous=editor.get_editor_world() if editor else None
previous=previous.get_path_name().split('.')[0] if previous else None
try:
    record()
    world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
    generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
    if len(generators)!=1:raise RuntimeError('Expected one production generator')
    generator=generators[0]
    before=generator.get_editor_property('module_catalog_json')
    catalog=json.loads(before)
    if not catalog.get('facility_flow'):raise RuntimeError('Facility recipe is not installed')
    rooms=[m for m in catalog['modules'] if m['id']=='AccumulatorControl']
    if len(rooms)!=1:raise RuntimeError('Expected one circular power room')
    package=PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap'
    digest=hashlib.sha256(package.read_bytes()).hexdigest()
    snapshot=ROOT/'Snapshots/LayoutFix20261008'
    snapshot.mkdir(parents=True,exist_ok=True)
    backup=snapshot/('L_Dungeon_Randomized-'+digest[:12]+'.umap')
    if not backup.exists():shutil.copy2(package,backup)
    (snapshot/('catalog-'+digest[:12]+'.json')).write_text(before,encoding='utf8')
    rooms[0]['port_seam_depth_cm']=35.
    catalog['facility_flow']['revision']=REVISION
    generator.modify()
    generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
    if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Production map save failed')
    (ROOT/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
    report.update(stage='map_saved',backup_map=str(backup),updated_room='AccumulatorControl',port_seam_depth_cm=35.)
    record()
    u.log('FACILITY_LAYOUT_FIX_SAVED '+TARGET)
except Exception:
    report['error']=traceback.format_exc();record();raise
finally:
    if previous and previous!=TARGET and previous.startswith('/Game/') and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        u.EditorLoadingAndSavingUtils.load_map(previous)
