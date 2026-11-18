"""Import R7 shutters and publish only the existing blacksmith assemblies."""
import hashlib,importlib,json,runpy,shutil,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/WindowR7'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve dirty map')
baseline=OUT/'publish-baseline.json'
if baseline.exists():
    expected=json.loads(baseline.read_text())['map_sha256']
    village=ROOT/'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
    if hashlib.sha256(village.read_bytes()).hexdigest()!=expected:
        active_module=Path(u.Paths.project_dir())/'Binaries/Win64/UnrealEditor-FPSGAME.dll'
        current_module=ROOT/'Binaries/Win64/UnrealEditor-FPSGAME.dll'
        if not current_module.exists() or hashlib.sha256(active_module.read_bytes()).digest()!=hashlib.sha256(current_module.read_bytes()).digest():
            raise RuntimeError('Village changed while queued; preserve it and refresh the native module before publishing')
# A completed shared build may already contain this batch. Require its reflected
# interface before touching the level; never save new geometry into an old class.
native=u.get_default_object(u.ColdSteelWindow)
native.get_editor_property('use_authored_hinges')
native.get_editor_property('authored_left_hinge')
backup=OUT/'Before';backup.mkdir(exist_ok=True)
for relative in ['Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap','Tools/WorldGeneration/VillageBlacksmith/LoftR3/assemble.py']:
    target=backup/Path(relative).name
    if not target.exists():shutil.copy2(ROOT/relative,target)
runpy.run_path(str(HERE/'prepare_materials.py'),run_name='__main__')
runpy.run_path(str(HERE/'import_assets.py'),run_name='__main__')
runpy.run_path(str(HERE/'prepare_window_wall.py'),run_name='__main__')
runpy.run_path(str(HERE.parent/'ChimneyR8/prepare_materials.py'),run_name='__main__')
runpy.run_path(str(HERE.parent/'ChimneyR8/import_assets.py'),run_name='__main__')
shutil.copy2(HERE/'assemble.py',HERE.parent/'LoftR3/assemble.py')
sys.path.insert(0,str(HERE.parent))
for name in ('LoftR3.assemble','author_shop'):
    if name in sys.modules:importlib.reload(sys.modules[name])
runpy.run_path(str(HERE.parent/'LoftR3/publish_revision.py'),run_name='__main__')
(OUT/'saved.json').write_text(json.dumps({'revision':'WindowR7b','chimney_revision':'ChimneyR8','map_saved':True,'interactive_windows':3,'swing_degrees':105,'hinge_reveal_offset_native_cm':26,'window_wall_collision':'complex-as-simple dedicated copy','default_state':'closed','repair_state_unchanged':True,'seed_changed':False,'runtime_checked':False},indent=2))
u.log('SMITH_WINDOW_R7_SAVED windows=3 map_saved=True')
if baseline.exists():baseline.unlink()
