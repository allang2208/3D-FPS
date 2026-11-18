"""Repair the outward window swing, housed braces and observed frame-material fallback."""
import os,json,runpy,shutil
from pathlib import Path
import unreal as u
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/LoftR3/ReviewFixR4';OUT.mkdir(parents=True,exist_ok=True)
before=OUT/'L_AbandonedVillage.before-window-and-brace-fix.umap'
if not before.exists():shutil.copy2(ROOT/'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap',before)
path='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/LoftR3/Meshes/SM_SmithLoft_ArcadeFrame_R4'
if not u.EditorAssetLibrary.does_asset_exist(path):
    os.environ['SMITH_LOFT_IMPORT_ROLE']='ArcadeFrame'
    try:runpy.run_path(str(HERE/'import_assets.py'),run_name='__main__')
    finally:os.environ.pop('SMITH_LOFT_IMPORT_ROLE',None)
mi=u.load_asset('/Game/UnrealNormandy/MaterialInstances/MI_RustyMetal_00A');base=mi.get_base_material()
was=base.get_editor_property('used_with_instanced_static_meshes')
base.set_editor_property('used_with_instanced_static_meshes',True)
u.MaterialEditingLibrary.recompile_material(base)
for material in (base,mi):
    if not u.EditorAssetLibrary.save_loaded_asset(material,False):raise RuntimeError('Save window material usage')
runpy.run_path(str(HERE/'publish_revision.py'),run_name='__main__')
(OUT/'saved.json').write_text(json.dumps(dict(window_direction='outward, right elevation +90 deg',shutter_yaw=[-35,35],shutter_outer_face_offset_source_cm=-40,
    braces='both west braces seated on real piers and beam',frame_mesh=path,material=base.get_path_name(),previous_instance_usage=was,map_saved=True),indent=2),encoding='utf-8')
