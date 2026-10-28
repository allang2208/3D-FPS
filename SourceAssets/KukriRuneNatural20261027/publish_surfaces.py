"""Bind only the three rune choices to their saved, isolated material versions."""
import json, shutil
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
receipt=json.loads((P/'import-receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:raise RuntimeError('Rune asset import has not completed.')
for relative in ('Content/ColdSteelData/kukri-modules.json',
                 'SourceAssets/KukriComponentVariants20261026/kukri-modules.json'):
    path=ROOT/relative
    original=path.read_bytes();data=json.loads(original.decode('utf-8-sig'))
    backup=P/'Before'/relative
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup)
    for key,materials in receipt['rune_surfaces'].items():
        data['slots']['blade_2'][key]['surface_materials']=materials
    data['surface_revision']=str(data.get('surface_revision','')).split('|RuneNatural20261027')[0]+'|RuneNatural20261027'
    if path.read_bytes()!=original:raise RuntimeError('Concurrent recipe change: '+str(path))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Saved '+str(path))
