"""Record the completed thumb correction, authored data and native build."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
attempt = max((p for p in OUT.glob('20*') if (p/'result.json').exists()), key=lambda p: p.name)
result = json.loads((attempt/'result.json').read_text(encoding='utf-8-sig'))
assert result['builds'] == 'Succeeded'
sources = ['Source/FPSGAME/Items/PotionUseMotion.h', 'Source/FPSGAME/Items/PotionUseMotion.cpp',
           'Source/FPSGAME/Items/PotionArmPose.cpp', 'Content/ColdSteelData/potion_use_motion.json',
           'SourceAssets/FoodGrip20261003/lamb_food_motion.py',
           'SourceAssets/FoodGrip20261003/lamb_thumb_profiles.json',
           'SourceAssets/LargeLamb20261014/grip_profile.json', 'SourceAssets/LambRibs20261014/grip_profile.json']
build_fixes = ['Source/FPSGAME/Production/'+name for name in
               ('ProductionBluntAuthority.cpp','ProductionBluntUppercut.cpp','ProductionBluntWhirlwind.cpp')]
sources += build_fixes
before = json.loads((OUT/'Before/Content/ColdSteelData/potion_use_motion.json').read_text())
after = json.loads((ROOT/'Content/ColdSteelData/potion_use_motion.json').read_text())
for item in ('roasted_large_lamb', 'roasted_lamb_ribs'):
    assert before[item]['times'] == after[item]['times']
    for digit in ('index', 'middle', 'ring', 'pinky'):
        assert before[item]['digits'][digit] == after[item]['digits'][digit]
builds = []
for target, binary in [('FPSGAMEEditor','UnrealEditor-FPSGAME.dll'), ('FPSGAME','FPSGAME.exe')]:
    if target == 'FPSGAMEEditor' and result.get('editor_skipped'):
        builds.append({'target':target, 'result':'Not completed',
                       'reason':'The Editor attempt failed in FoodSpoilageAuditCommandlet; the source was subsequently corrected, but an interactive editor is now open. Module replacement is deferred.',
                       'log':'SourceAssets/LambThumbClose20261015/20261015-220910/FPSGAMEEditor.log'})
        continue
    log = attempt/(target+'.log')
    text = log.read_text(encoding='utf-8-sig', errors='replace')
    assert 'Result: Succeeded' in text
    assert (ROOT/'Binaries/Win64'/binary).stat().st_mtime >= max((ROOT/p).stat().st_mtime for p in sources if p.startswith('Source/'))
    builds.append({'target':target, 'result':'Succeeded', 'log':str(log.relative_to(ROOT)),
                   'mode':'up_to_date' if 'Target is up to date' in text else 'compile_and_link',
                   'origin':result.get('build_origin','this task')})
report = {'builds':builds, 'saved_contacts':json.loads((OUT/'saved-contacts.json').read_text()),
          'files_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
          'four_finger_angles_and_action_clocks_preserved':True,
          'required_build_fixes':build_fixes,
          'lift_approach_cm': {'large_lamb':6, 'lamb_ribs':6},
          'runtime_or_visual_acceptance':False, 'game_or_editor_started_by_this_task':False}
(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'builds':builds,'receipt':str(OUT/'delivery.json')}))
