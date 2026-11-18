"""Install and save the scoped shop detail revision in the current editor or commandlet."""
import importlib,json,runpy,shutil,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/DetailR6'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Preserve active PIE; exit play before saving DetailR6')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map changes before DetailR6 publish')
before=OUT/'Before/L_AbandonedVillage.umap'
if not before.exists():shutil.copy2(ROOT/'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap',before)
runpy.run_path(str(HERE/'prepare_materials.py'),run_name='__main__')
runpy.run_path(str(HERE/'import_assets.py'),run_name='__main__')
# Switch the maintained generator only once all new package references exist on disk.
shutil.copy2(HERE/'assemble.py',HERE.parent/'LoftR3/assemble.py')
sys.path.insert(0,str(HERE.parent))
for name in ('LoftR3.assemble','author_shop'):
 if name in sys.modules:importlib.reload(sys.modules[name])
runpy.run_path(str(HERE.parent/'LoftR3/publish_revision.py'),run_name='__main__')
assets=json.loads((OUT/'assets-saved.json').read_text())
(OUT/'saved.json').write_text(json.dumps({
 'revision':'DetailR6','map_saved':True,'level':'/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage',
 'meshes_saved':assets['saved'],'window':'remove duplicated cross-frame; shutters with seated hinges and native stone reveal',
 'guardrails':'both return-landing ends and wall-side upper well edge completed',
 'barrel':'actual oak material HISM usage enabled',
 'chimney':'full bonded stone courses, narrow recessed mortar, native stone blend weights imported explicitly',
 'ruined':'same open workshop footprint; original fractured upper bay, broken timber and fallen masonry; no living furniture',
 'sign_dimensions_cm':[150,66],'sign_scale_from_previous':1.5,'sign_paint':'hand-painted hammer/anvil and Chinese brush lettering',
 'default_state':'ruined','seed_changed':False,'gameplay_tested':False,'engine_preview_rendered':False},ensure_ascii=False,indent=2),encoding='utf-8')
u.log('SMITH_DETAIL_R6_SAVED meshes=5 map_saved=True')
