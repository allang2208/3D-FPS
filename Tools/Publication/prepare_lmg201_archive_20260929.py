"""One-time 2026-09-29 inventory, not a recurring cleanup command.

The final plan also records the seven superseded root metadata files moved after
the initial batch. The current root README is their replacement, not a retiree.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'SourceAssets/LMG20120260927'
OUT = ROOT / 'Docs/Weapons/lmg201-publication-20260929'
OUT.mkdir(parents=True, exist_ok=True)
ARCHIVE = 'trash/lmg201-rejected-20260929'
if (ROOT / ARCHIVE).exists():
    raise SystemExit('Archive already completed; preserve the recorded plan and current README.')

# Captured native donors and the new Meshy lineage remain outside the archive.
# Old construction recipes may need restoration to reproduce a rejected version.
retired = {
    'InputsV01', 'ReferenceV01', 'Meshy', 'ModelV01', 'Authoring',
    'Refinement01', 'Refinement02', 'Hands03', 'Charging04', 'Support05',
    'PKMDirect09', 'Cover10', 'Reload11', 'Camera13', 'ReloadFraming15',
    'Joint16', 'WholeArm17', 'Framing20', 'FixedRail23', 'Surface25',
    'BodyRollback27',
}
moves = []
for directory in sorted(retired):
    for p in sorted((SOURCE / directory).rglob('*')):
        if p.is_file():
            moves.append(dict(source=p.relative_to(ROOT).as_posix(),
                reason='Retired first-model geometry or superseded adjustment; not the new Meshy201 recovery entry',
                replacement='Repair36 + retained native donor snapshots'))

# Refine12's surface packet is still used by the original magazine grip author.
for p in sorted((SOURCE / 'Refine12').rglob('*')):
    if p.is_file() and p.name != '201_surface.json':
        moves.append(dict(source=p.relative_to(ROOT).as_posix(),
            reason='Old cover/arm authoring superseded; retain 201_surface.json for Magazine24 contact source',
            replacement='Repair36; Magazine24'))

# Preserve the native rig input loaded by Install30; retire Video26's rejected
# rendered shell outputs and material attempt, keeping its reference frames.
for p in sorted((SOURCE / 'Video26').rglob('*')):
    if p.is_file() and (p.parent.name in {'Exports', 'Before'} or p.name == 'LMG201_Video26_HighLow.blend'):
        moves.append(dict(source=p.relative_to(ROOT).as_posix(),
            reason='Rejected Video26 surface/output; editable rig donor stays for Install30',
            replacement='Install30/Surface32/Repair36'))

for p in sorted(SOURCE.rglob('*')):
    if not p.is_file() or p.parts[len(SOURCE.parts)] in retired | {'Refine12','Video26'}:
        continue
    # Automatic Blender backup and prior failed D35 lid outputs are not inputs
    # to Repair36, which reads the pre-thickness recipe, Work and textures.
    rejected_d35 = p.parent.name == 'Exports' and p.name in {
        'SK_LMG201_D35_Installed.fbx', 'SK_LMG201_D35_Weapon.fbx'}
    if p.suffix == '.blend1' or rejected_d35 or p.name == 'LMG201_D35_Editable.blend':
        moves.append(dict(source=p.relative_to(ROOT).as_posix(),
            reason='Superseded snapshot or D35 unbounded inner-wall result',
            replacement='Repair36/LMG201_R36_Lid.blend; Repair36/Exports/SK_LMG201_R36_Installed.fbx'))

retired_content = {'ArmSprint06','Charging04','Hands03','Refinement01','Refinement02','Skin07','PKMDirect09','Reload11','Video26','Support05'}
candidates=[]
for p in sorted((ROOT/'Content/Weapons/LMG201').rglob('*.uasset')):
    relative=p.relative_to(ROOT).as_posix()
    within=p.relative_to(ROOT/'Content/Weapons/LMG201').parts
    if within[0] in retired_content or any(x.lower() in {'previous','backups','backup','before'} for x in within[:-1]):
        candidates.append(relative)

plan=dict(archive_root=ARCHIVE, moves=moves, content_candidates=candidates,
    retained_source_contract={
        'Skin07 and ArmSprint06':'Native donor snapshot and precursor retained, not an accepted original gun body',
        'BeltFeed08':'Current base animation and private skeleton lineage; original metal-box reload is retired',
        'PKMFK19':'Accessories22 editable donor input, not the active cloth reload',
        'Video26/LMG201_Video26_Editable.blend':'Install30 loads its native rig; rejected shell must not be reinstalled',
        'Refine12/201_surface.json':'Magazine24 grip source packet',
        'Detail35/model.py, Work, Textures and controls':'Repair36 directly uses pre-thickness geometry; D35 material parents remain active',
        'MeshyRetry28 through Repair36':'Current new-model production chain',
    }, scope='201 lineage only; no gameplay, rendering or build tests')
(OUT/'archive-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'source_files':len(moves),'source_bytes':sum((ROOT/m['source']).stat().st_size for m in moves),'content_candidates':len(candidates)}))
