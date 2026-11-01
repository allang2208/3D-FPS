import json,copy
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]
receipt=json.loads((O/'import_receipt.json').read_text());assert receipt['complete']
path=P/'Content/ColdSteelData/modular_outfits.json';original=path.read_bytes();data=json.loads(original)
backup=O/'before_modular_outfits.json'
if not backup.exists():backup.write_bytes(original)
old='/Game/Weapons/M24/Repair20261027/SK_M24_RepairedV9.SK_M24_RepairedV9'
def descend(node):
    if not isinstance(node,dict):return False
    if old in node:
        profile=copy.deepcopy(node[old]);profile['hide_source_materials']=receipt['arm_materials']
        node[receipt['mesh']]=profile;return True
    return any(descend(v) for v in node.values())
assert descend(data),'Retained M24 outfit profile missing'
assert path.read_bytes()==original,'Concurrent change; rerun registration'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M24_HOLD_PROFILE_SAVED',receipt['mesh'],receipt['arm_materials'])
