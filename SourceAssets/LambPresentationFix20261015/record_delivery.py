"""Record the saved changes and completed native builds for this correction."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
attempt = max((p for p in OUT.glob('20*') if (p/'result.json').exists()), key=lambda p: p.name)
result = json.loads((attempt/'result.json').read_text(encoding='utf-8-sig'))
assert result['builds'] == 'Succeeded'
sources = [
    'Source/FPSGAME/Building/CampfireCookingPresentation.cpp',
    'Content/ColdSteelData/potion_use_motion.json',
    'SourceAssets/FoodGrip20261003/lamb_food_motion.py',
    'SourceAssets/LambRibs20261014/author_lamb_grip.py',
    'SourceAssets/LambRibs20261014/grip_profile.json',
    'SourceAssets/LargeLamb20261014/author_large_lamb_grip.py',
    'SourceAssets/LargeLamb20261014/grip_profile.json',
    'SourceAssets/LargeLamb20261014/grip-production.json',
]
builds = []
for target, binary in [('FPSGAMEEditor', 'UnrealEditor-FPSGAME.dll'), ('FPSGAME', 'FPSGAME.exe')]:
    log = attempt/(target+'.log')
    text = log.read_text(encoding='utf-8-sig', errors='replace')
    assert 'Result: Succeeded' in text
    path = ROOT/'Binaries/Win64'/binary
    assert path.stat().st_mtime >= (ROOT/sources[0]).stat().st_mtime
    builds.append({'target': target, 'result': 'Succeeded',
                   'mode': 'up_to_date' if 'Target is up to date' in text else 'compile_and_link',
                   'log': str(log.relative_to(ROOT)),
                   'binary': str(path.relative_to(ROOT))})
geometry = json.loads((OUT/'geometry-review.json').read_text())
report = {
    'scope': 'Lamb spit penetration and first-person eating orientation/framing',
    'files_sha256': {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in sources},
    'builds': builds,
    'geometry_review': {item: {'before': data['before']['summary'], 'after': data['after']['summary'],
                             'clocks_unchanged': data['clocks_unchanged']} for item, data in geometry['foods'].items()},
    'mesh_or_texture_packages_changed': False,
    'editor_or_game_started': False,
    'rendered_or_live_visual_acceptance': False,
}
(OUT/'delivery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'builds': [b['target']+' Succeeded' for b in builds], 'receipt': str(OUT/'delivery.json')}))
