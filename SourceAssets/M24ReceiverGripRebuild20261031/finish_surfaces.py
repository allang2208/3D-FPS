import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent
R=json.loads((O/'install_receipt.json').read_text())
if not R['complete']:raise RuntimeError('Finish the mesh import before surface authoring')
R['tangent_basis_saved']=[]
for path in R['saved']:
 if '/Meshes/' not in path:continue
 mesh=u.load_asset(path)
 if not u.M24ChassisAssetTools.bake_stock_tangent_basis(mesh):raise RuntimeError('Tangent basis authoring failed '+path)
 if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+path)
 R['tangent_basis_saved'].append(path)
 (O/'install_receipt.json').write_text(json.dumps(R,indent=2))
print('M24_RECEIVER_GRIP_SURFACES_SAVED',len(R['tangent_basis_saved']),flush=True)
