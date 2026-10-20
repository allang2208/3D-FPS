"""Batches 2-4: viewmodels (pose sources), their companions by rig profile, clip discovery by skeleton in UE.

python batch_plan.py batch2|batch3|batch4 -> <batch>.json
Companion meshes take every viewmodel that can lead them (all weapons sharing the rig profile) as pose
sources: grips from all of their held clips, validation on all of their clips.
"""
import json, sys
from rollout import R, P

BATCHES = {
    'batch2': dict(view={
        'M1911': '/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny',
        'G18': '/Game/Weapons/G18/Integrated20260929/Single/SK_G18_Manny',
        'PitViper': '/Game/Weapons/PitViper2011/Integrated20261002/Single/SK_PitViper2011_Manny',
        'DW715': '/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny',
        'RSH12': '/Game/Weapons/RSH12/SK_RSH12_Manny',
        'RSH12_DA': '/Game/Weapons/RSH12/DoubleAction20261003/single/SK_RSH12_Manny',
        'RSH12_N': '/Game/Weapons/RSH12/Native71520261003/single/SK_RSH12_Manny',
        'M1911_l': '/Game/Weapons/PistolDualWield20260914/M1911/l/SK_Dual_M1911_l',
        'M1911_r': '/Game/Weapons/PistolDualWield20260914/M1911/r/SK_Dual_M1911_r',
        'DW715_l': '/Game/Weapons/PistolDualWield20260914/DW715/l/SK_Dual_DW715_l',
        'DW715_r': '/Game/Weapons/PistolDualWield20260914/DW715/r/SK_Dual_DW715_r',
        'G18_l': '/Game/Weapons/G18/Integrated20260929/Dual/l/SK_Dual_G18_l',
        'G18_r': '/Game/Weapons/G18/Integrated20260929/Dual/r/SK_Dual_G18_r',
        'PitViper_l': '/Game/Weapons/PitViper2011/Integrated20261002/Dual/l/SK_Dual_PitViper2011_l',
        'PitViper_r': '/Game/Weapons/PitViper2011/Integrated20261002/Dual/r/SK_Dual_PitViper2011_r',
        'RSH12_l': '/Game/Weapons/RSH12/Dual/l/SK_Dual_RSH12_l', 'RSH12_r': '/Game/Weapons/RSH12/Dual/r/SK_Dual_RSH12_r',
        'RSH12_DA_l': '/Game/Weapons/RSH12/DoubleAction20261003/l/SK_Dual_RSH12_l', 'RSH12_DA_r': '/Game/Weapons/RSH12/DoubleAction20261003/r/SK_Dual_RSH12_r',
        'RSH12_N_l': '/Game/Weapons/RSH12/Native71520261003/l/SK_Dual_RSH12_l', 'RSH12_N_r': '/Game/Weapons/RSH12/Native71520261003/r/SK_Dual_RSH12_r'},
        rigs={'M1911': ['M1911', 'G18', 'PitViper'], 'M1911_l': ['M1911_l', 'G18_l', 'PitViper_l'], 'M1911_r': ['M1911_r', 'G18_r', 'PitViper_r'],
              'DW715': ['DW715', 'RSH12', 'RSH12_DA', 'RSH12_N'], 'DW715_l': ['DW715_l', 'RSH12_l', 'RSH12_DA_l', 'RSH12_N_l'],
              'DW715_r': ['DW715_r', 'RSH12_r', 'RSH12_DA_r', 'RSH12_N_r']}),
    'batch3': dict(view={
        'RuneSword': '/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny',
        'RuneArms': '/Game/Weapons/AzureRunesword20260913/Modules20260919/SK_RuneSword_Arms',
        'FrostSword': '/Game/Weapons/FrostCrystalSword20260915/SK_FrostCrystalSword_Manny',
        'FrostArms': '/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms',
        'Axe': '/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe',
        'Pickaxe': '/Game/Items/ProductionTools/RusticPickaxe20260919/SK_RusticPickaxe',
        'Warhammer': '/Game/Weapons/SteelWarhammer20261014/SK_SteelWarhammer_BareArmsV7',
        'WarhammerSprint': '/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1',
        'Traversal': '/Game/Characters/ModularOutfit20260924/BarePalmV7/Traversal/SK_Traversal_BareArmsV7',
        'TraversalBounds': '/Game/Movement/Traversal/Native/SK_TraversalArms_AnimatedBounds',
        'Bow': '/Game/Weapons/DarkBow20260925/ArmsV4/SK_Bow_BareArmsV7',
        'BowContact': '/Game/Weapons/DarkBow20260925/ContactV9/SK_Bow_BareArmsV7'},
        rigs={'RuneSword': ['RuneSword', 'RuneArms'], 'FrostSword': ['FrostSword'], 'FrostArms': ['FrostArms'], 'Axe': ['Axe'],
              'Pickaxe': ['Pickaxe', 'Warhammer', 'WarhammerSprint'], 'Traversal': ['Traversal', 'TraversalBounds'], 'Bow': ['Bow', 'BowContact']}),
    'batch4': dict(view={
        'Super90': '/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7',
        'M870': '/Game/Weapons/M870/Tactical20261015/SK_M870_V7'},
        rigs={'Super90': ['Super90', 'M870']},
        extra=[('/Game/Weapons/M870/Arms20261016/SK_M870_BareArmsV7', ['M870']),
               ('/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90/SK_Super90_skin_ue_field_gloves', ['Super90'])]),
}
name = sys.argv[1]; B = BATCHES[name]
cfg = json.loads((P / 'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
used = set(json.loads((R / 'scope_candidates.json').read_text())['used'])
by_rig = {}
for vm, prof in cfg['profiles'].items():
    if not isinstance(prof, dict): continue
    for k in ('base', 'native_bare_skin', 'bare_arms_candidate'):
        if prof.get(k): by_rig.setdefault(prof.get('rig_profile'), set()).add(prof[k].split('.')[0])
for item in cfg['items'].values():
    for k in ('skin_meshes', 'rig_meshes'):
        for rig, path in (item.get(k) or {}).items(): by_rig.setdefault(rig, set()).add(path.split('.')[0])
views = set(B['view'].values()); meshes = []; done = set()
for n, vm in B['view'].items():
    if vm in done: continue
    meshes.append(dict(mesh=vm, pose_sources=[n], role='viewmodel')); done.add(vm)
for rig, sources in B['rigs'].items():
    for pk in sorted(by_rig.get(rig, [])):
        if pk in used and pk not in done:
            meshes.append(dict(mesh=pk, pose_sources=sources, role='companion')); done.add(pk)
for pk, sources in B.get('extra', []):
    if pk not in done: meshes.append(dict(mesh=pk, pose_sources=sources, role='companion')); done.add(pk)
for m in meshes:
    if m['role'] == 'viewmodel':
        for rig, sources in B['rigs'].items():
            if m['pose_sources'][0] in sources: m['pose_sources'] = [m['pose_sources'][0]]
PISTOL = ['/Game/Weapons/DualPistolQuickCombat20260920/', '/Game/Weapons/PistolDualWield20260914/', '/Game/Weapons/PistolLocomotion20260914/']
ROOTS = {**{k: ['/Game/Weapons/RSH12/'] + PISTOL for k in ('RSH12', 'RSH12_DA', 'RSH12_N', 'RSH12_l', 'RSH12_r', 'RSH12_DA_l', 'RSH12_DA_r', 'RSH12_N_l', 'RSH12_N_r')},
         **{k: ['/Game/Weapons/DanWesson715/'] + PISTOL for k in ('DW715', 'DW715_l', 'DW715_r')},
         'Traversal': ['/Game/Movement/'], 'TraversalBounds': ['/Game/Movement/']}
plan = dict(viewmodels=B['view'], clips={k: {} for k in B['view']}, held={}, meshes=meshes, discover=True,
            clip_roots={k: v for k, v in ROOTS.items() if k in B['view']})
(R / (name + '.json')).write_text(json.dumps(plan, indent=1))
print(len(meshes), 'meshes')
for m in meshes: print(' ', m['role'], m['pose_sources'], m['mesh'])
