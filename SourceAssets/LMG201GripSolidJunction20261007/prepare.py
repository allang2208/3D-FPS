import hashlib,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];previous=O.parent/'LMG201GripJunction20261007'
C=json.loads((previous/'install_receipt.json').read_text())['meshes'];(O/'Input').mkdir(parents=True,exist_ok=True);(O/'Exports').mkdir(exist_ok=True)
for key,row in C.items():
 asset=P/'Content'/(row['path'].removeprefix('/Game/')+'.uasset')
 if hashlib.sha256(asset.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Current asset changed since junction export '+key)
 source=Path(row['fbx']);target=O/'Input'/source.name;shutil.copy2(source,target);row['fbx']=str(target)
(O/'input.json').write_text(json.dumps(C,indent=2))
print('SOLID_JUNCTION_SOURCE_READY',len(C))
