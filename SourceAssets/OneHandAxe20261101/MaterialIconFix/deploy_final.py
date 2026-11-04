"""Deploy the visually reviewed UE catalog image and record the saved result."""
import hashlib,json,shutil
from pathlib import Path
from PIL import Image

P=Path(__file__).resolve().parent
project=P.parents[2]
source=P/'Catalog/ue_tactical_hatchet.png'
mesh=json.loads((P/'mesh_save_receipt.json').read_text('utf-8'))
if not mesh['saved']:raise RuntimeError('Corrected mesh was not saved')
im=Image.open(source).convert('RGBA')
bounds=im.getchannel('A').getbbox()
if not bounds:raise RuntimeError('Catalog image is empty')
width,height=im.size
icon={'size':[width,height],'alpha_bounds':list(bounds),
      'dominant_axis_fill':max((bounds[2]-bounds[0])/width,(bounds[3]-bounds[1])/height),
      'alpha_center':[(bounds[0]+bounds[2])*.5,(bounds[1]+bounds[3])*.5],
      'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
      'visually_reviewed':True,'pipeline':'ColdSteelWeaponIconCatalog'}
targets=[project/'Content/ColdSteelData/Icons/ue_tactical_hatchet.png',P.parent/'Icons/ue_tactical_hatchet.png']
for target in targets:shutil.copy2(source,target)
icon['deployed']=[str(t) for t in targets]
r=json.loads((P/'delivery.json').read_text('utf-8'))
r.update(status='saved_and_deployed',ue_mesh_correction_saved=True,final_inventory_png_deployed=True,
         final_import_mode='background_commandlet',startup_sdk_setup_skipped_for_asset_process_only=True,
         headless_import_requests_sent=1,mesh_save_receipt=mesh,icon=icon,pending=[])
(P/'delivery.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
original=P.parent/'import_receipt.json'
backup=P/'Before/import_receipt.json'
if not backup.exists():shutil.copy2(original,backup)
receipt=json.loads(original.read_text('utf-8'))
receipt['normal_correction_saved']=True
receipt['inventory_icon_pipeline']='ColdSteelWeaponIconCatalog'
receipt['material_icon_fix_receipt']='MaterialIconFix/delivery.json'
original.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({'mesh_saved':True,'icon':icon,'gameplay_tested':False},ensure_ascii=False))
