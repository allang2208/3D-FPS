"""Read local source-package presence and raw package references; never import/save assets."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = [
    'NiagaraExamples/FX_Misc/NS_Fire',
    'Vefects/Free_Fire/Shared/Particles/NS_Fire_Medium',
    'Vefects/Free_Fire/Shared/Particles/NS_Fire_Small',
    'MilitaryTrench/Particles/P_Fire',
    'EasyBuildingSystem/Effects/PS_CampFire',
    '_SplineVFX/NS/NS_Spline_Fire',
]
out = {'method': 'Read files and manifest/archive member names. Raw strings establish references only; runtime property values are in local-fire-inventory.json.',
       'packages': [], 'vault_roots': [], 'external_fire_archive_members': [], 'engine_templates': []}
for package in PACKAGES:
    path = ROOT / 'Content' / (package + '.uasset')
    blob = path.read_bytes()
    out['packages'].append({'package': '/Game/' + package, 'file': str(path),
        'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest(),
        'raw_game_references': sorted(set(v.decode('ascii') for v in re.findall(rb'/Game/[A-Za-z0-9_./]+', blob)))})
vault = ROOT.parent / 'VaultCache'
out['vault_roots'] = sorted(p.name for p in vault.iterdir() if p.is_dir())
out['known_source_copies'] = [str(p) for p in [
    vault / 'PerfectFbbf41cddaf26V1/data/Content/Vefects/Free_Fire/Shared/Particles/NS_Fire_Medium.uasset',
    vault / 'SplineVF0c12c9b3d930V1/data/Content/_SplineVFX/NS/NS_Spline_Fire.uasset',
    vault / 'EasyBuila55ea970921aV10/data/Content/EasyBuildingSystem/Effects/PS_CampFire.uasset',
    ROOT.parent / 'EasyBuildingSystemV10/Content/EasyBuildingSystem/Effects/PS_CampFire.uasset',
    vault / 'Untitlede28cc9a0a786V1/data/Content/DoorSystem/Demo/StarterContent/Particles/P_Fire.uasset',
] if p.is_file()]
for archive in (ROOT.parent / '资产').rglob('*.zip'):
    try:
        with zipfile.ZipFile(archive) as z:
            members = [n for n in z.namelist() if re.search(r'(?:campfire|bonfire|flame|subuv|flipbook|fireplace|(?:^|[/_])fire(?:[/_.]))', n, re.I)]
        if members: out['external_fire_archive_members'].append({'archive': str(archive), 'members': members[:100]})
    except (OSError, zipfile.BadZipFile):
        pass
engine = Path('E:/Program Files (x86)/UE_5.8/Engine/Plugins/FX/NiagaraFluids/Content')
out['engine_templates'] = [str(p) for p in engine.glob('Templates/Gas/**/Systems/*Fire*.uasset')]
target = ROOT / 'SourceAssets/Campfire20261012/local-fire-source-inventory.json'
target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'project_candidates': len(out['packages']), 'source_copies': len(out['known_source_copies']),
                  'archive_hits': len(out['external_fire_archive_members']), 'engine_templates': len(out['engine_templates'])}))
