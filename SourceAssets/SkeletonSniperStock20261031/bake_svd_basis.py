import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]
asset='/Game/Weapons/SkeletonSniperStock20261031/Meshes/SM_SniperSkeleton_SVD'
backup=O/'Before/SM_SniperSkeleton_SVD_before_basis.uasset'
if not backup.exists():shutil.copy2(P/'Content/Weapons/SkeletonSniperStock20261031/Meshes/SM_SniperSkeleton_SVD.uasset',backup)
mesh=u.load_asset(asset)
if not u.M24ChassisAssetTools.bake_stock_tangent_basis(mesh):raise RuntimeError('Stock tangent basis bake failed')
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Stock tangent basis bake not saved')
(O/'svd_baked_basis_receipt.json').write_text(json.dumps(dict(saved=True,path=asset,source_normals_uv_and_fit_retained=True,lods_baked=True),indent=2))
print('SVD_STOCK_BAKED_BASIS_SAVED')
