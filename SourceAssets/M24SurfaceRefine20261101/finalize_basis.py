"""Finish the UV-seam tangent basis on this batch's saved corner-normal repair."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).resolve().parent
report=json.loads((O/'install_receipt.json').read_text(encoding='utf-8'))
if not report['complete']:raise RuntimeError('Surface installation is incomplete')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def disk(path):return Path(u.Paths.project_content_dir())/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
for row in report['saved_meshes']:
    if row.get('tangent_basis_finalized'):continue
    path=row['path']
    if path in dirty or hashlib.sha256(disk(path).read_bytes()).hexdigest()!=row['sha256']:
        raise RuntimeError('Concurrent mesh edit retained '+path)
for row in report['saved_meshes']:
    if row.get('tangent_basis_finalized'):continue
    path=row['path'];asset=u.load_asset(path)
    backup=O/'BeforeTangentFinalize'/disk(path).name;backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(disk(path),backup)
    if not u.M24ChassisAssetTools.bake_stock_tangent_basis(asset):raise RuntimeError('Tangent basis authoring failed '+path)
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Mesh save failed '+path)
    row['tangent_basis_finalized']=True;row['sha256']=hashlib.sha256(disk(path).read_bytes()).hexdigest()
    (O/'install_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('M24_TANGENT_BASIS_SAVED',path,flush=True)
