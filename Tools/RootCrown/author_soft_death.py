"""Independent Root Crown cage and anatomical support release; no simulation."""
import json,sys
from pathlib import Path
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/MonsterSoftCorpse')
import author_cages
author_cages.ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014/SoftDeathV01')
for item in json.loads((author_cages.ROOT/'sources.json').read_text('utf8')):
    author_cages.author(item)
    folder=author_cages.ROOT/item['key'];cage=json.loads((folder/'cage.json').read_text('utf8'))
    legs=['Bone_002','Bone_003','Bone_005','Bone_006','Bone_007','Bone_009','Bone_010','Bone_011']
    rims=[f'Crown_{i:02d}_Rim' for i in range(1,11)]
    cage.update(collapse_in_place=True,unsupported_source_bones=legs+rims,unsupported_min_weight=.55)
    (folder/'cage.json').write_text(json.dumps(cage,separators=(',',':')),encoding='utf8')
    (folder/'anatomy.json').write_text(json.dumps(dict(released_bones=legs+rims,retained='central torso, stem and proximal crown volume',weight_threshold=.55,tested=False),indent=2),encoding='utf8')
print('ROOT_CROWN_SOFT_CAGE_AUTHORED')
