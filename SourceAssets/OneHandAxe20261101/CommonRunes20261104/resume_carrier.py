"""Resume only the carrier after this batch's 35 successful material/texture saves."""
from pathlib import Path
import json,ast
import unreal as u
P=Path(__file__).resolve().parent;L=u.EditorAssetLibrary
CARRIER='/Game/Weapons/TacticalHatchet20261101/ModulesV1/SM_TacticalHatchet_Head_Factory_RuneCarrier'
if CARRIER in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Unsaved factory carrier preserved')
source=json.loads((P/'sources.json').read_text('utf-8'))
heads=[json.loads((P/(h['kind']+'.json')).read_text('utf-8')) for h in source['heads']]
receipt=json.loads((P/'import_receipt.json').read_text('utf-8'))
root='/Game/Weapons/TacticalHatchet20261101/CommonRunes20261104'
receipt['heads']=[{'id':h['id'],'slot':h['target_slot'],'source_mesh':h['mesh']} for h in heads]
for h in heads:
    for r in source['runes']:
        name='MI_HatchetMark_'+h['kind']+'_'+r['kind']
        path=root+'/Materials/'+name+'.'+name
        if path not in receipt['saved_assets']:raise RuntimeError('Resume requires saved material '+path)
        receipt['rune_surfaces'][r['id']][h['target_slot']]=path
script=P/'import_assets.py';code=script.read_text('utf-8')
tree=ast.parse(code)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='save'],type_ignores=[]),str(script),'exec'),globals())
exec(compile(code[code.index('# The factory head shares'):],str(script),'exec'),globals())
