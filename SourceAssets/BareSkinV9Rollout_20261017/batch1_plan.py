"""Batch 1 (rifles): meshes, their pose-source viewmodel, and the clips that drive them.

Clip lists come from the shared weapon-animation manifest (base + per-foregrip-family authored roles);
SVD and the legacy LMG201 viewmodel come from their weapon asset headers. Writes batch1.json.
"""
import json, glob
from pathlib import Path
from rollout import R, P

man = json.loads((P / 'SourceAssets/WeaponAnimationSharing20261001/manifest.json').read_text())
cfg = json.loads((P / 'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
used = set(json.loads((R / 'scope_candidates.json').read_text())['used'])
VIEW = {'M4': '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416', 'HK416': '/Game/Weapons/HK416/Reworked20260930/SK_HK416_Manny',
        'AKM': '/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative', 'QBZ191': '/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny',
        'ASH12': '/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface', 'M16': '/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny',
        'A762': '/Game/Weapons/A762/Integrated20260920/SK_A762_Manny', 'PKM': '/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular',
        'LMG201': '/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10', 'LMG201_Manny': '/Game/Weapons/LMG201/Production20260927/SK_LMG201_Manny',
        'SVD': '/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock'}
clips = {k: {} for k in VIEW}
for p in man['profiles']:
    for name, path in VIEW.items():
        if p['mesh'] == path:
            for pair in p['pairs']:
                clips[name].setdefault(pair['role'], pair['base'])
                clips[name]['%s:%s' % (p['family'], pair['role'])] = pair['authored']
def folder_clips(pattern):
    out = {}
    for f in glob.glob(str(P / 'Content' / pattern)):
        pk = '/Game/' + Path(f).relative_to(P / 'Content').with_suffix('').as_posix()
        out[Path(f).stem] = pk
    return out
clips['SVD'] = folder_clips('Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_*.uasset')
clips['LMG201_Manny'] = folder_clips('Weapons/LMG201/BeltFeed08/Animations/A_LMG201_*.uasset')
held = {k: [c for r, c in v.items() if r == 'idle' or r.endswith(':idle') or r.endswith('_idle') and 'reload' not in r] for k, v in clips.items()}
held['SVD'] = [c for r, c in clips['SVD'].items() if r.endswith('_idle')]
held['LMG201_Manny'] = [c for r, c in clips['LMG201_Manny'].items() if r.endswith('_idle')]
# companion meshes per rig profile
profiles = {}
for vm, prof in cfg['profiles'].items():
    if not isinstance(prof, dict): continue
    rig = prof.get('rig_profile'); vm = vm.split('.')[0]
    for k in ('base', 'native_bare_skin', 'bare_arms_candidate'):
        if prof.get(k): profiles.setdefault(rig, set()).add(prof[k].split('.')[0])
for item in cfg['items'].values():
    for k in ('skin_meshes', 'rig_meshes'):
        for rig, path in (item.get(k) or {}).items(): profiles.setdefault(rig, set()).add(path.split('.')[0])
RIG = {'M4': 'M4', 'HK416': 'M4', 'AKM': 'AKM', 'QBZ191': 'QBZ191', 'ASH12': 'ASH12', 'M16': 'M16', 'A762': 'A762', 'PKM': 'PKM', 'LMG201': 'PKM', 'LMG201_Manny': 'PKM', 'SVD': 'SVD'}
meshes = []
for name, vm in VIEW.items():
    if name != 'M4': meshes.append(dict(mesh=vm, pose_source=name, role='viewmodel'))
done = {m['mesh'] for m in meshes}
for name in ('M4', 'AKM', 'QBZ191', 'ASH12', 'M16', 'A762', 'PKM', 'SVD'):
    for pk in sorted(profiles.get(RIG[name], [])):
        if pk in used and pk not in done:
            meshes.append(dict(mesh=pk, pose_source=name, role='companion')); done.add(pk)
plan = dict(viewmodels=VIEW, clips=clips, held=held, meshes=meshes)
(R / 'batch1.json').write_text(json.dumps(plan, indent=1))
print(len(meshes), 'meshes'); [print(' ', m['pose_source'], m['role'], m['mesh']) for m in meshes]
print({k: len(v) for k, v in clips.items()}); print({k: v for k, v in held.items()})
