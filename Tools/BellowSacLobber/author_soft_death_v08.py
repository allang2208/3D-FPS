"""Build Bellow-specific positive tetrahedral bindings using the shared authoring algorithm."""
import json
import sys
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
sys.path.insert(0, str(PROJECT / 'Tools/MonsterSoftCorpse'))
import author_cages

author_cages.ROOT = PROJECT / 'SourceAssets/BellowSacLobberMeshy20261012/SoftDeathV08'
chains = {
    'rear_left': ['Bone_008', 'Bone_007', 'Bone_006', 'Bone_005', 'Bone_004'],
    'rear_right': ['Bone_014', 'Bone_013', 'Bone_012', 'Bone_011', 'Bone_010'],
    'front_left': ['Bone_021', 'Bone_020', 'Bone_019', 'Bone_018'],
    'front_right': ['Bone_026', 'Bone_025', 'Bone_024', 'Bone_023'],
    'nozzle': ['Bone_030', 'Bone_029', 'Bone_028'],
}
for item in json.loads((author_cages.ROOT / 'sources.json').read_text(encoding='utf-8')):
    author_cages.author(item)
    folder = author_cages.ROOT / item['key']
    cage = json.loads((folder / 'cage.json').read_text(encoding='utf-8'))
    cage.update(collapse_in_place=True, unsupported_source_bones=sorted({b for bones in chains.values() for b in bones}),
                unsupported_min_weight=.65)
    (folder / 'cage.json').write_text(json.dumps(cage, separators=(',', ':')), encoding='utf-8')
    (folder / 'anatomy.json').write_text(json.dumps(dict(released_chains=chains,
        retained='pelvis, chest, dorsal sac and proximal limb joints',
        source_weight_threshold=.65, tested=False), indent=2), encoding='utf-8')
