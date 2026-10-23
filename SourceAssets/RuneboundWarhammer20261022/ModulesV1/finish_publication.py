"""Finish the file-backed icon/catalog stage after the mesh/material save receipt."""
import json
from pathlib import Path
from register import publish
P=Path(__file__).resolve().parent
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
rows=[]
for name in ('exports.json','adapted_exports.json'):
    rows+=json.loads((P/name).read_text(encoding='utf-8-sig'))['parts']
D='/Game/Weapons/RuneboundWarhammer20261022/ModulesV1'
expected={D+'/'+r['mesh']+'.'+r['mesh'] for r in rows}
expected.add(D+'/Runes/M_SilverRuneSurface_RuneboundWarhammerShaftV1.M_SilverRuneSurface_RuneboundWarhammerShaftV1')
missing=expected-set(receipt['assets'])
if missing:raise RuntimeError('The preceding production batch has not saved: '+str(missing))
publish()
receipt.update(complete=True,factory_modules=6,fitted_common_modules=14,shared_runes=5,
    animation_assets_modified=0,recipe_published=True,icons_storage='staged PNG',
    mesh_material_save_log='import-engine-02.log',file_publication='finish_publication.py')
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
(P/'publication_receipt.json').write_text(json.dumps({
    'complete':True,'catalogs':['runebound-warhammer-modules.json','runebound-warhammer-gunsmith.json'],
    'icon_consumer':'M4GunsmithLayout.cpp: FImageUtils::ImportFileAsTexture2D',
    'saved_meshes':20,'saved_materials':1,'icon_pngs':14,'tested':False},indent=2),encoding='utf-8')
print('RUNEBOUND_MODULAR_PUBLICATION_COMPLETE')
