"""Scoped publication/retirement for the warhammer inspect + normal combo V5-V7 work.

classify  prints the HEAD diff opcodes of shared files with an ownership guess.
prepare   reconstructs each shared file without this task's edits (named baseline),
          writes shared-integration.patch, the source/local manifests and the
          retirement plan. Baselines stay local under Saved/; only hashes publish.
archive   moves only the planned files into trash, verifying SHA-256 read-back.
No operation builds or runs UE; staging and pushing are explicit Git steps.
"""
import argparse
import difflib
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'SourceAssets/SteelWarhammer20261014'
OUT = ROOT / 'Docs/Publication/WarhammerInspectCombo20261016'
LOCAL = ROOT / 'Saved/WarhammerInspectComboPublication20261016'
TRASH = ROOT / 'trash/warhammer-inspect-combo-retired-20261016'

MARKERS = re.compile(r'Inspect|BluntClipTime|BluntChain|BluntStartClip|HandOffBluntPose|PredictBluntEnemyContact|'
                     r'RealForWindupClip|MeleeRelease|BufferedCutTolerance')

# Files fully attributable to this task, published at their source paths.
OWNED = [
    'Source/FPSGAME/Production/ProductionBluntInspect.cpp',
    'Source/FPSGAME/Production/WarhammerInspectWalkCues.h',
    'Source/FPSGAME/Production/ProductionBluntFlow.cpp',
    'Source/FPSGAME/Production/ProductionBluntComboTiming.h',
    'Source/FPSGAME/Characters/FPSPlayerBodyNetwork.cpp',   # HEAD diff is only this task's hunk
]

# Shared files: this task's edits, reversed on the current text to obtain the
# named baseline. (anchor, line count, original text) removes/restores a block;
# ('=', new, old) restores a substring inside a line. Applied in order; every
# anchor must be unique when applied.
S = '='
SHARED = {
    'Source/FPSGAME/Production/ProductionToolComponent.h': [
        ('    /** Warhammer inspect: cosmetic real-time clock', 5, ''),
        ('    /** V6 ordinary cut: clip seconds of the current attack', 14, ''),
        ('    float InspectElapsed=-1.f, WalkInspectDelay=2.5f;', 7, ''),
        ("    /** Owner-side cosmetic prediction of the server's", 4, ''),
    ],
    'Source/FPSGAME/Production/ProductionToolComponent.cpp': [
        ('#include "WarhammerInspectWalkCues.h"', 1, ''),
        ('    const FSoftObjectPath WarhammerInspectPath(', 2, ''),
        (S, ' Feedback.Reset(); ScheduleWalkInspect(false);', ' Feedback.Reset();'),
        ('        Paths.Add(WarhammerInspectPath);', 4, ''),
        ('                    Motions.Add(TEXT("Inspect"),', 2, ''),
        (S, 'bQueuedBluntAttack=false;BluntStartClip=0.f;', 'bQueuedBluntAttack=false;'),
        ('    const bool Chain=Queued&&bBluntChain;', 2, ''),
        ('    // The chained cut has already shown its early load', 7, ''),
        (S, ' EquipElapsed=-1; InspectElapsed=-1; bContacted=false;', ' EquipElapsed=-1; bContacted=false;'),
        ('    bBluntChain=false;BluntStartClip=0.f;', 1, ''),
        ("        // V6 hammer cuts: the sound follows each stage's downswing", 6,
         '        const float WhooshTime=bBluntHeavy?BluntLiftSeconds():\n'
         '            (Kind==TEXT("warhammer")?ProductionBluntCombo::WhooshTime(ContactSeconds):Kind==TEXT("axe")?AxeMotion.SwingSoundSeconds:\n'
         '            (UsesPickaxeMotion()?FMath::Max(0.f,ContactSeconds-.10f):ContactSeconds*.65f))/RateScale;\n'),
        ('            // Networked ordinary hammer cuts settle on the server timer;', 4, ''),
        ('        AdvanceBluntChain(Delta,End);', 1, ''),
    ],
    'Source/FPSGAME/Production/ProductionToolMotion.cpp': [
        ('        if(MatchedNormal&&!bBluntHandoffEntry)', 3,
         '        if(MatchedNormal)\n'
         '            if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->ClearWhirlwindEntry();\n'),
        ('        // An interrupted inspect can be mid-turn', 2, ''),
        ("                // A visual chain hands the turnaround into the next cut's load", 2, ''),
        (S, 'Clip==TEXT("Inspect")||Clip==TEXT("InspectWalk")?.14f:Clip==TEXT("ActiveSwing")', 'Clip==TEXT("ActiveSwing")'),
        (S, '(!bBluntHeavy&&!bBluntCharging&&Elapsed>=0.f)||LeavingInspect);', '!bBluntHeavy&&!bBluntCharging&&Elapsed>=0.f);'),
        ('    // Every action, sprint, jump or dodge takes over from the cosmetic inspect.', 2, ''),
        ('    TickWalkInspect(Delta);', 1, ''),
        ('        // Buffered next cut: its load is already visible', 3,
         '        if(bBluntHeavy)SampleMotion(TEXT("ActiveSwing"),Authored);\n'),
        (S, 'Kind==TEXT("warhammer")?BluntClipTime():',
         'Kind==TEXT("warhammer")?ProductionBluntCombo::SwingSourceTime(Authored,ContactSeconds,SwingSeconds):'),
        ('    else if(InspectElapsed>=0.f)', 14, ''),
        ('        ProductionBluntCombo::SampleCamera(bHitConfirmed?BluntHitClipTime()', 9,
         '        ProductionBluntCombo::SampleCamera(AuthoredElapsed(),ContactSeconds,SwingSeconds,BluntStage,bHitConfirmed,Location,Rotation);\n'),
    ],
    'Source/FPSGAME/Production/ProductionAxeContact.cpp': [
        ('#include "../Weapons/RuneSwordHitQuery.h"', 1, ''),
        ('bool UProductionToolComponent::PredictBluntEnemyContact() const', 13, ''),
    ],
    'Source/FPSGAME/FPSGAMECharacterActionPriority.cpp': [
        ('    // The warhammer inspect is a presentation clock only', 2, ''),
    ],
    'Source/FPSGAME/FPSGAMECharacter.cpp': [
        ('    if(auto* Tools=FindComponentByClass<UProductionToolComponent>();Tools&&Tools->IsWarhammerEquipped())', 6, ''),
    ],
    'Source/FPSGAME/Characters/FPSPlayerBodyActions.cpp': [
        ('                // Non-linear clip clock: report its real rate', 8,
         '                Timed(Diagonal?EFPSBodyAction::Strike:EFPSBodyAction::HeavyStrike,\n'
         '                    ProductionBluntCombo::SwingSourceTime(ToolTime,Tool->ContactSeconds,Tool->SwingSeconds),\n'
         '                    ProductionBluntCombo::SwingSeconds,Tool->RateScale);\n'
         '                State.ContactFraction=ProductionBluntCombo::ContactSeconds/ProductionBluntCombo::SwingSeconds;\n'),
    ],
    'Source/FPSGAME/Characters/FPSBodyMeleePose.h': [
        (S, 'ProductionBluntCombo::Effort(Time,Hit,Load,Follow,Side>0.f?0:Side<0.f?1:2);',
         'ProductionBluntCombo::Effort(Time,Hit,Load,Follow);'),
    ],
    'Source/FPSGAME/Production/ProductionBluntAuthority.cpp': [
        ('    // A buffered cut leaves the owner on the frame its previous cut ends', 9,
         '    if(!World||bBluntUppercut||bBluntWhirlwind||!CanCommitBlunt(Pawn,Profile)||World->GetTimeSeconds()<BluntServerReadyAt){Reject();return;}\n'),
        (S, 'const float Contact=float(Early)+(Heavy?Lift+WarhammerHeavy::Contact/ActionRate:float(Stats.ContactSeconds)-Resume);',
         'const float Contact=Heavy?Lift+WarhammerHeavy::Contact/ActionRate:float(Stats.ContactSeconds)-Resume;'),
        (S, 'BluntServerReadyAt=Now+Early+(Heavy?', 'BluntServerReadyAt=World->GetTimeSeconds()+(Heavy?'),
        ('    // The server owns the combo stage; a chained cut predicted another stage.', 2, ''),
        ('        // The owner already predicted this hit at contact', 2, ''),
        ('        // A late confirmation can arrive after a miss chain already began.', 2, ''),
    ],
}
# Untracked shared header: the pre-task V4 text (reconstructed verbatim from the
# read before the first edit), kept local; only its hash is published.
SHARED_BASELINE_FILES = {'Source/FPSGAME/Production/ProductionBluntCombo.h': LOCAL / 'ProductionBluntCombo.h.V4-reconstructed'}

ACTIVE_RECIPES = ['InspectV1', 'InspectWalkSpeedV3', 'NormalComboSwapV5', 'NormalComboRhythmV7']
RETIRE_DIRS = {
    'InspectWalkV1': 'Walking inspect V1 (24 deg right-hand overshoot) rejected by the user; replaced by WristV2 then SpeedV3 (self-contained).',
    'InspectWalkWristV2': 'Walking inspect V2 superseded by InspectWalkSpeedV3 at user request; SpeedV3 does not read it.',
    'NormalComboFlowV6': 'Normal combo V6 rejected by the user (release too slow, weak impact); replaced by NormalComboRhythmV7, which reads V4/V5 only.',
    'InspectWalkSpeedV3/Before': 'Snapshot of the superseded WristV2 runtime clip.',
    'NormalComboSwapV5/Before': 'Snapshot of the replaced right-hand-top stage-2 clips; the pose source remains in NormalComboV4.',
    'NormalComboRhythmV7/Before': 'Snapshot of the rejected V6 runtime clips and V6 headers.',
    'NormalComboSwapV5/Diagnosis/Frames': 'Per-frame diagnosis renders; the contact sheets and scripts remain.',
}
RUN_LOGS = ['author-run.txt', 'build-run.txt', 'import-wait.txt', 'plan-run.txt', 'import-bridge-01.txt']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text(path):
    return Path(path).read_text(encoding='utf-8-sig').replace('\r\n', '\n')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def patch(rel, old, new):
    return ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), 'a/' + rel, 'b/' + rel, n=3))


def reverse(rel, current):
    lines = current.splitlines(True)
    for spec in SHARED[rel]:
        if spec[0] == S:
            _, new, old = spec
            hits = [i for i, l in enumerate(lines) if new in l]
            if len(hits) != 1:
                raise RuntimeError(f'{rel}: substring not unique ({len(hits)}): {new}')
            lines[hits[0]] = lines[hits[0]].replace(new, old)
            continue
        anchor, count, old = spec
        hits = [i for i, l in enumerate(lines) if l.startswith(anchor)]
        if len(hits) != 1:
            raise RuntimeError(f'{rel}: anchor not unique ({len(hits)}): {anchor}')
        i = hits[0]
        lines[i:i + count] = old.splitlines(True)
    return ''.join(lines)


def classify():
    for rel in SHARED:
        try:
            old = git('show', 'HEAD:' + rel).decode('utf-8-sig').replace('\r\n', '\n')
        except subprocess.CalledProcessError:
            print('==', rel, '(untracked)');continue
        a, b = old.splitlines(True), text(ROOT / rel).splitlines(True)
        operations = [x for x in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if x[0] != 'equal']
        print('==', rel, len(operations), 'ops')
        for index, (tag, i1, i2, j1, j2) in enumerate(operations):
            changed = a[i1:i2] + b[j1:j2]
            mine = sum(1 for l in changed if MARKERS.search(l))
            print(f'  [{index}] {tag} -{i2-i1} +{j2-j1} {"mine?" if mine else ""}: ' + (b[j1] if j2 > j1 else a[i1]).strip()[:100])


def files_under(rel_dir):
    root = ASSETS / rel_dir
    return sorted(p for p in root.rglob('*') if p.is_file())


def prepare():
    OUT.mkdir(parents=True, exist_ok=True);LOCAL.mkdir(parents=True, exist_ok=True)
    if (OUT / 'archive-manifest.json').exists():
        raise RuntimeError('Already archived; do not regenerate the dated plan')
    baseline = git('rev-parse', 'HEAD').decode().strip()
    records, combined = [], ''
    for rel in OWNED:
        data = (ROOT / rel).read_bytes()
        records.append({'path': rel, 'publication': 'source path', 'local_sha256': sha(data), 'bytes': len(data)})
    for rel in list(SHARED) + list(SHARED_BASELINE_FILES):
        current = text(ROOT / rel)
        if rel in SHARED_BASELINE_FILES:
            old = text(SHARED_BASELINE_FILES[rel]);source = 'reconstructed V4 text before the first edit (local only)'
        else:
            old = reverse(rel, current);source = 'current file with this task\'s edits reversed (local only)'
        (LOCAL / (Path(rel).name + '.baseline')).write_text(old, encoding='utf-8')
        body = patch(rel, old, current)
        if not body:raise RuntimeError('No task change found in ' + rel)
        combined += body
        records.append({'path': rel, 'publication': 'shared-integration.patch', 'baseline': source,
                        'baseline_lf_sha256': sha(old.encode()), 'local_lf_sha256': sha(current.encode()),
                        'note': 'Mixed with other warhammer/parallel work not on the public main; only this task\'s hunks are in the patch'})
    (OUT / 'shared-integration.patch').write_text(combined, encoding='utf-8')
    recipes, local_assets = [], []
    for name in ACTIVE_RECIPES:
        for p in files_under(name):
            rel = p.relative_to(ROOT).as_posix()
            if any(rel.startswith((ASSETS / d).relative_to(ROOT).as_posix() + '/') for d in RETIRE_DIRS) or p.name in RUN_LOGS:
                continue
            data = p.read_bytes()
            entry = {'path': rel, 'sha256': sha(data), 'bytes': len(data)}
            (recipes if p.suffix in {'.py', '.ps1', '.md'} else local_assets).append(entry)
    for rel_dir in ['Content/Weapons/SteelWarhammer20261014/InspectV1']:
        for p in sorted((ROOT / rel_dir).glob('*.uasset')):
            data = p.read_bytes();local_assets.append({'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(data), 'bytes': len(data)})
    for n in ('Slash1', 'Slash1Recover', 'Slash2', 'Slash2Recover', 'Slash3', 'Slash3Recover'):
        p = ROOT / f'Content/Weapons/SteelWarhammer20261014/NormalComboV4/A_Warhammer_{n}.uasset'
        data = p.read_bytes();local_assets.append({'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(data), 'bytes': len(data),
                                                   'revision': 'NormalComboRhythmV7_20261015'})
    save_json(OUT / 'source-manifest.json', {'git_baseline': baseline, 'files': records, 'recipes': recipes})
    save_json(OUT / 'local-assets.json', {'scope': 'Local-only binaries, receipts and measurements; not redistributed. Hashes only.',
                                          'files': local_assets})
    plan = []
    for rel_dir, reason in RETIRE_DIRS.items():
        for p in files_under(rel_dir):
            plan.append({'source': p.relative_to(ROOT).as_posix(), 'reason': reason})
    for name in ACTIVE_RECIPES:
        for log in RUN_LOGS:
            p = ASSETS / name / log
            if p.exists():
                plan.append({'source': p.relative_to(ROOT).as_posix(), 'reason': 'Console run log duplicated by the stage receipts/plan JSON.'})
    for entry in plan:
        p = ROOT / entry['source'];data = p.read_bytes()
        entry.update({'target': (TRASH / Path(entry['source']).relative_to('SourceAssets/SteelWarhammer20261014')).relative_to(ROOT).as_posix(),
                      'bytes': len(data), 'sha256': sha(data)})
    save_json(OUT / 'archive-plan.json', {'trash_root': TRASH.relative_to(ROOT).as_posix(), 'files': plan,
                                          'kept': ACTIVE_RECIPES + ['NormalComboV4 (pose source of V7)', 'SprintDragV1/WhirlwindInertiaV8 (AST-read helpers)']})
    print(f'prepared: {len(records)} source records, {len(recipes)} recipes, {len(local_assets)} local assets, {len(plan)} files to retire')


def archive():
    plan = json.loads(text(OUT / 'archive-plan.json'))
    moved = []
    for entry in plan['files']:
        src, dst = ROOT / entry['source'], ROOT / entry['target']
        if not str(src.resolve()).startswith(str(ASSETS.resolve())) or not str(dst.resolve()).startswith(str(TRASH.resolve())):
            raise RuntimeError('Outside authorised roots: ' + entry['source'])
        if sha(src.read_bytes()) != entry['sha256']:
            raise RuntimeError('Changed since planning: ' + entry['source'])
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():raise RuntimeError('Target exists: ' + entry['target'])
        shutil.move(str(src), str(dst))
        if sha(dst.read_bytes()) != entry['sha256']:
            raise RuntimeError('Read-back mismatch: ' + entry['target'])
        moved.append(dict(entry, verified=True))
    for rel_dir in sorted(RETIRE_DIRS, key=len, reverse=True):
        d = ASSETS / rel_dir
        for sub in sorted((x for x in d.rglob('*') if x.is_dir()), key=lambda x: len(x.parts), reverse=True) if d.exists() else []:
            if not any(sub.iterdir()):sub.rmdir()
        if d.exists() and not any(d.iterdir()):d.rmdir()
    save_json(OUT / 'archive-manifest.json', {'trash_root': plan['trash_root'], 'moved': moved,
                                              'files': len(moved), 'bytes': sum(m['bytes'] for m in moved),
                                              'permanent_deletion': False})
    print(f'archived {len(moved)} files, {sum(m["bytes"] for m in moved)} bytes; all read-backs verified')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['classify', 'prepare', 'archive'])
    command = parser.parse_args().command
    {'classify': classify, 'prepare': prepare, 'archive': archive}[command]()


if __name__ == '__main__':
    main()
