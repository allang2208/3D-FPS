"""Finish the already imported mesh after the production helper's necessary native build."""
import json
from pathlib import Path
import unreal as u
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/OneHandAxe20261101')
mesh=u.load_asset('/Game/Weapons/TacticalHatchet20261101/SM_TacticalHatchet')
if not u.TacticalHatchetImportLibrary.finalize_mesh(mesh): raise RuntimeError('Hatchet tangent authoring failed')
if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False): raise RuntimeError('Hatchet save failed')
r=json.loads((P/'import_receipt.json').read_text('utf-8'))
r['tangent_basis_authored']=True
(P/'import_receipt.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
u.log('HATCHET_FINAL_SAVED '+mesh.get_path_name())
