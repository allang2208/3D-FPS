"""Build the merged shoeing tools and save a private village level for publication."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import unreal as u

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
BATCH = Path(os.environ['VILLAGE_SHOP_REST_BATCH'])
HOST = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if HOST!=BATCH/'Host':
    raise RuntimeError('A private village map is required')
sys.path[:0] = [str(PROJECT/'Tools/WorldGeneration'/p) for p in
                 ('AbandonedVillage','VillageBlacksmith','VillageBakery','VillageGunshop')]
from BenchWork.layout import PACKAGE
from BenchWork.shoeing_tools import model
from gunshop_shell_author import build_mesh
from shop_rest_layout import apply

mesh, slots, materials = build_mesh(model())
iron = u.load_asset('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Workfloor/Materials/M_SmithScaleIron')
if not iron:
    raise RuntimeError('Missing smith forged-iron finish')
materials[slots.index('Iron')] = iron
options = u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,
    enable_recompute_tangents=True,enable_collision=False,enable_nanite=False)
asset = u.EditorAssetLibrary.load_asset(PACKAGE) if u.EditorAssetLibrary.does_asset_exist(PACKAGE) else None
if not asset:
    asset,status = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh,PACKAGE,options)
    if status!=u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not create '+PACKAGE)
write = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
    replace_materials=True,new_materials=materials,new_material_slot_names=slots)
_,status = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(mesh,asset,write,u.GeometryScriptMeshWriteLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS or not u.EditorAssetLibrary.save_loaded_asset(asset,False):
    raise RuntimeError('Could not save '+PACKAGE)

level = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
relative = level.removeprefix('/Game/')+'.umap'
original = HOST/'Content'/relative
digest = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before = digest(original)
backup = BATCH/'Before'/before/original.name
backup.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(original,backup)
world = u.EditorLoadingAndSavingUtils.load_map(level)
if not world:
    raise RuntimeError('Village map unavailable')
placements = apply(PROJECT)
if not u.EditorLoadingAndSavingUtils.save_map(world,level):
    raise RuntimeError('Could not save village shop fittings')
for key in (relative,PACKAGE.removeprefix('/Game/')+'.uasset'):
    dest = BATCH/'Saved'/key
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(HOST/'Content'/key,dest)
(BATCH/'staged.json').write_text(json.dumps(dict(revision='ShopFurnitureRestR1',level=level,packages=[PACKAGE],
    placements=placements,map_before=before,map_after=digest(original),before=str(backup)),indent=2),encoding='utf-8')
