"""Publish only large-lamb thumbs, with matching rebuild data."""
import json,copy,hashlib
from pathlib import Path
O=Path(__file__).parent;R=O.parents[1]
candidate=json.loads((O/'candidate_motion.json').read_text(encoding='utf-8'))
paths=[('Content/ColdSteelData/potion_use_motion.json','roasted_large_lamb'),('SourceAssets/FoodGrip20261003/large_lamb_natural_grasp.json',None),('SourceAssets/LargeLamb20261014/grip_profile.json',None)]
note='LambGripV8_20261017: verified current Traversal V8 surface at retained BareArmsV7 asset path; independently fitted native local thumb rotations with Y-axis MCP/IP flexion and continuous local closure; food trajectory, palms, four fingers and 6s/4.65s clock preserved.'
rows=[]
for relative,family in paths:
    path=R/relative;before=O/'Before'/relative
    if path.read_bytes()!=before.read_bytes():raise RuntimeError('Concurrent edit since backup: '+relative)
    data=json.loads(path.read_text(encoding='utf-8-sig'));motion=data[family] if family else data
    for field in ('digits','right_digits'):motion[field]['thumb']=copy.deepcopy(candidate[field]['thumb'])
    motion['authoring']=note
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    rows.append(dict(path=relative,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(O/'data_receipt.json').write_text(json.dumps(rows,indent=2))
print('LAMB_V8_GRIP_DATA_SAVED',len(rows))
