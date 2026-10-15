"""Scoped publication/retirement manifest for the 2026-10-15 warhammer work.

prepare writes reviewable patches and a retirement plan; archive moves only that
plan, verifying hashes and resolved roots. Neither operation builds or runs UE.
Staging and pushing are deliberately separate, explicit Git operations.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'SourceAssets/SteelWarhammer20261014'
OUT = ROOT / 'Docs/Publication/WarhammerCombat20261015'
LOCAL = ROOT / 'Saved/WarhammerPublication20261015'
TRASH = ROOT / 'trash/warhammer-combat-retired-20261015'
EXCLUDED = {'ModulesV1', 'InspectV1', 'InspectWalkV1', 'InspectWalkWristV2',
            'InspectWalkSpeedV3', 'NormalComboSwapV5', 'NormalComboFlowV6', 'NormalComboRhythmV7'}
REJECTED = {'NormalComboV2', 'NormalComboV3'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text(path):
    return path.read_text(encoding='utf-8-sig')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def patch(rel, old, new):
    return ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                      'a/' + rel, 'b/' + rel, n=3))


def replay(old, new, selected):
    a, b = old.splitlines(True), new.splitlines(True)
    operations = [x for x in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
                  if x[0] != 'equal']
    for index in sorted(selected, reverse=True):
        _, start, end, left, right = operations[index]
        a[start:end] = b[left:right]
    return ''.join(a)


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    if (OUT / 'archive-manifest.json').exists():
        raise RuntimeError('This dated publication has already been archived; do not regenerate its historical plan')
    if (OUT / 'source-manifest.json').exists():
        for entry in json.loads(text(OUT / 'source-manifest.json'))['files']:
            current = ROOT / entry['path']
            if entry.get('local_sha256') and sha(current.read_bytes()) != entry['local_sha256']:
                raise RuntimeError('Publication input changed; re-review ownership: ' + entry['path'])
            if entry.get('local_lf_sha256') and sha(text(current).encode()) != entry['local_lf_sha256']:
                raise RuntimeError('Shared input changed; re-review ownership: ' + entry['path'])
    baseline = git('rev-parse', 'HEAD').decode().strip()
    records, selected_files, candidates = [], [], {}

    # Original dedicated modules. Parallel inspect/ordinary-flow code is excluded.
    dedicated = '''ProductionBluntContact.cpp ProductionBluntGuard.cpp
ProductionBluntHeavy.cpp ProductionBluntQuickCombat.cpp ProductionBluntSprint.cpp
ProductionBluntUppercut.cpp ProductionBluntWhirlwind.cpp ProductionBluntWhirlwindFocus.cpp
ProductionToolMeshComponent.cpp ProductionToolMeshComponent.h WarhammerAudioPaths.h
WarhammerCombat.cpp WarhammerCombat.h WarhammerGuardMotion.h WarhammerHeadMarker.h
WarhammerHeavyMotion.h WarhammerNetworkAuditCommandlet.cpp WarhammerNetworkAuditCommandlet.h
WarhammerQuickCombatMarker.h WarhammerQuickCombatMotion.h WarhammerShockwave.cpp
WarhammerShockwave.h WarhammerSlamFXSubsystem.cpp WarhammerSlamFXSubsystem.h
WarhammerSprintAuditCommandlet.cpp WarhammerSprintAuditCommandlet.h WarhammerUppercutArc.h
WarhammerUppercutMotion.h'''.split()
    for name in dedicated:
        selected_files.append('Source/FPSGAME/Production/' + name)
    selected_files += ['Source/FPSGAME/Weapons/RuneSwordToolGuard.cpp',
                       'Source/FPSGAME/Skills/WarhammerQuickCombat.cpp']

    # Shared files against Git HEAD: only the inspected warhammer hunks.
    owned = {
        'Production/ProductionAxeContact.cpp': 'all',
        'Production/ProductionAxeLocomotion.cpp': 'all',
        'Skills/FPSQuickCombatComponent.h': 'all',
        'Skills/FPSQuickCombatComponent.cpp': [1, 6, 7, 8, 9, 10, 11, 12],
        'FPSGAMECharacterActionPriority.cpp': [1],
    }
    root_patch = ''
    for part, indexes in owned.items():
        rel = 'Source/FPSGAME/' + part
        old = git('show', baseline + ':' + rel).decode('utf-8-sig').replace('\r\n', '\n')
        current = text(ROOT / rel)
        result = current if indexes == 'all' else replay(old, current, indexes)
        if result == current and part != 'Production/ProductionAxeContact.cpp':
            candidates[rel] = result
        else:
            records.append({'path': rel, 'publication': 'quick-and-tool-git-integration.patch',
                            'baseline': baseline + ':' + rel, 'baseline_lf_sha256': sha(old.encode()),
                            'candidate_lf_sha256': sha(result.encode()), 'local_lf_sha256': sha(current.encode()),
                            'note': 'Mixed latest development preserved; no older reconstructed file staged at its source path'})
        root_patch += patch(rel, old, result)
    (OUT / 'quick-and-tool-git-integration.patch').write_text(root_patch, encoding='utf-8')

    # Guard + network shared integration uses exact, named pre-change snapshots.
    # Do not publish unrelated food, shotgun, inspect or V6/V7 combo edits.
    choices = {
        'Production/ProductionToolComponent.cpp': [0, 1, 2, 3, 4, 5, 9, 11, 12, 15],
        'Production/ProductionToolComponent.h': [0, 1, 3, 4],
        'Production/ProductionToolMotion.cpp': [0, 1, 4, 6, 7, 8],
        'Weapons/RuneSwordComponent.cpp': 'all',
        'Weapons/RuneSwordComponent.h': 'all',
        'Weapons/RuneSwordGuard.cpp': 'all',
        'Weapons/RuneSwordGuardNetwork.cpp': 'all',
        'Characters/FPSPlayerBodyActions.cpp': [0],
        'Movement/FPSPlayerDodge.cpp': 'all',
        'FPSGAMECharacter.cpp': [17, 19],
        'Multiplayer/ColdSteelPlayerState.h': [3, 4],
        'Multiplayer/ColdSteelQuickCombatAuthority.cpp': 'all',
        'Production/ProductionBluntAuthority.cpp': 'all',
    }
    guard_patch = ''
    for part, indexes in choices.items():
        rel = 'Source/FPSGAME/' + part
        network_base = part.startswith('Multiplayer/') or part == 'Production/ProductionBluntAuthority.cpp'
        base = ASSETS / ('NetworkReviewV1' if network_base else 'GuardV1') / 'Before' / rel
        old = text(base)
        lines = old.splitlines(True)
        current_lines = text(ROOT / rel).splitlines(True)
        blocks = [{'a0': i, 'a1': j, 'old': ''.join(lines[i:j]), 'new': ''.join(current_lines[k:l])}
                  for tag, i, j, k, l in difflib.SequenceMatcher(None, lines, current_lines, autojunk=False).get_opcodes()
                  if tag != 'equal']
        indexes = range(len(blocks)) if indexes == 'all' else indexes
        for index in sorted(indexes, reverse=True):
            block = blocks[index]
            if ''.join(lines[block['a0']:block['a1']]) != block['old']:
                raise RuntimeError('Named baseline changed: ' + rel)
            lines[block['a0']:block['a1']] = block['new'].splitlines(True)
        result = ''.join(lines)
        guard_patch += patch(rel, old, result)
        records.append({'path': rel, 'publication': 'guard-network-named-baseline.patch',
                        'baseline': base.relative_to(ROOT).as_posix(), 'baseline_lf_sha256': sha(old.encode()),
                        'candidate_lf_sha256': sha(result.encode()),
                        'local_lf_sha256': sha(text(ROOT / rel).encode()),
                        'owned_change_blocks': list(indexes)})
    (OUT / 'guard-network-named-baseline.patch').write_text(guard_patch, encoding='utf-8')

    # Minimal compile repairs from this review, without the unrelated feature bodies.
    repairs = {
        'Building/SmeltingSystem.h': [('    void LoadCampfireRecipes();',
             '    friend void RunCampfireFoodSpoilageAudit(UWorld* World,UColdSteelStatusModel* Model,TFunctionRef<void(bool,const FString&)> Check);\n    void LoadCampfireRecipes();')],
        'Building/VoxelBuildGeometry.cpp': [('Convex.VertexBuffer', 'Convex.VertexData'),
             ('\n    TMap<FIntVector,uint8> NoShapes;', '\n    TMap<FIntVector,uint8> EmptyShapes;'),
             ('MoveTemp(NoShapes),Radius', 'MoveTemp(EmptyShapes),Radius')],
        'Items/FoodSpoilageAuditCommandlet.cpp': [('FJsonSerializer::Serialize(Report.ToSharedRef(),TJsonWriterFactory<>::Create(&Json))', 'FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json))')],
    }
    fixes = ''
    for part, replacements in repairs.items():
        rel = 'Source/FPSGAME/' + part
        base = ASSETS / 'NetworkReviewV1/Before' / rel
        old = text(base)
        result = old
        for before, after in replacements:
            if before not in result:
                raise RuntimeError('Compile prerequisite anchor missing: ' + rel + ': ' + before)
            result = result.replace(before, after)
        fixes += patch(rel, old, result)
        records.append({'path': rel, 'publication': 'build-prerequisites.patch',
                        'baseline': base.relative_to(ROOT).as_posix(),
                        'baseline_lf_sha256': sha(old.encode()), 'candidate_lf_sha256': sha(result.encode())})
    for name in ['ColdSteelAlchemyBookWidget.cpp', 'ColdSteelAlchemyBookPreview.cpp']:
        rel = 'Source/FPSGAME/UI/' + name
        base = ASSETS / 'NetworkReviewV1/Before' / rel
        old, new = text(base), text(ROOT / rel)
        # Each observed changed block must only rename the local slot variable.
        import re
        replacement = 'ColumnSlot' if name.endswith('Widget.cpp') else 'LoadingSlot'
        a, b = old.splitlines(True), new.splitlines(True)
        for tag, i, j, k, l in reversed(difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()):
            if tag != 'equal' and re.sub(r'\bSlot\b', replacement, ''.join(a[i:j])) == ''.join(b[k:l]):
                a[i:j] = b[k:l]
        result = ''.join(a)
        if old == result:
            raise RuntimeError('No isolated slot rename: ' + rel)
        fixes += patch(rel, old, result)
        records.append({'path': rel, 'publication': 'build-prerequisites.patch',
                        'baseline': base.relative_to(ROOT).as_posix(),
                        'baseline_lf_sha256': sha(old.encode()), 'candidate_lf_sha256': sha(result.encode())})
    (OUT / 'build-prerequisites.patch').write_text(fixes, encoding='utf-8')

    for p in sorted(ASSETS.rglob('*')):
        if not p.is_file():
            continue
        parts = p.relative_to(ASSETS).parts
        if parts[0] in EXCLUDED | REJECTED or 'Before' in parts or '__pycache__' in parts:
            continue
        if p.suffix.lower() in {'.py', '.ps1', '.hlsl', '.md'} or (p.name.startswith('prompt') and p.suffix == '.txt'):
            selected_files.append(p.relative_to(ROOT).as_posix())
    # Historical design records, omitting parallel modifications and inspect/normal-flow.
    for p in sorted((ROOT / 'Docs/Weapons').glob('steel-warhammer*.md')):
        if any(s in p.name for s in ['balance-', 'modules-', 'inspect-', 'combo-flow-v6', 'combo-rhythm-v7', 'combo-swap-v5']):
            continue
        selected_files.append(p.relative_to(ROOT).as_posix())

    for rel, result in candidates.items():
        p = LOCAL / 'candidates' / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(result, encoding='utf-8')
        selected_files.append(rel)
    for rel in selected_files:
        p = ROOT / rel
        records.append({'path': rel, 'publication': 'original-path',
                        'local_sha256': sha(p.read_bytes()),
                        'candidate_lf_sha256': sha(candidates[rel].encode()) if rel in candidates else None,
                        'bytes': len(candidates[rel].encode()) if rel in candidates else p.stat().st_size})
    save_json(OUT / 'source-manifest.json', {'git_baseline': baseline, 'files': records,
        'excluded_parallel_stages': sorted(EXCLUDED),
        'note': 'Named-baseline patches require full local combat/profile prerequisites; this public slice is not a clean-clone build receipt.'})
    save_json(LOCAL / 'stage-plan.json', {'baseline': baseline, 'paths': sorted(set(selected_files)),
                                        'candidate_paths': sorted(candidates)})

    plan = []
    def retire(p, reason, replacement):
        rel = p.relative_to(ROOT)
        plan.append({'original': rel.as_posix(), 'destination': (TRASH / rel).relative_to(ROOT).as_posix(),
                     'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes()),
                     'reason': reason, 'replacement': replacement})
    for p in sorted(ASSETS.rglob('*')):
        if not p.is_file():
            continue
        parts = p.relative_to(ASSETS).parts
        if parts[0] in EXCLUDED:
            continue
        if parts[0] in REJECTED:
            retire(p, 'User rejected V2/V3 arm chain; no active source consumer outside these retired stages.',
                   'SourceAssets/SteelWarhammer20261014/NormalComboV4; later parallel normal-combo stages preserved')
        elif 'Before' in parts:
            retire(p, 'Superseded pre-change snapshot; no current authoring input reads this backup.',
                   'Current original path or the owning stage author/import source; named baselines retained by this archive')
        elif parts[0] == 'NetworkReviewV1' and (p.name in {
            'build-FPSGAME-first.log', 'build-FPSGAME-second.log', 'build-FPSGAME-third.log',
            'build-FPSGAME-fourth.log', 'build-FPSGAME-fifth.log', 'build-before-final-receipt.json',
            'editor-state.txt'} or '-backup-' in p.name):
            retire(p, 'Superseded failed build or duplicate audit log; final receipts retained.',
                   'SourceAssets/SteelWarhammer20261014/NetworkReviewV1/delivery.json')
    for stage in sorted(REJECTED):
        for p in sorted((ROOT / 'Content/Weapons/SteelWarhammer20261014' / stage).rglob('*')):
            if p.is_file():
                retire(p, 'Rejected V2/V3 animation package; production and authoring references now use other clips.',
                       'Content/Weapons/SteelWarhammer20261014/NormalComboV4')
    save_json(OUT / 'archive-plan.json', {'files': plan, 'count': len(plan), 'bytes': sum(x['bytes'] for x in plan)})
    # Hash-only inventory: local input/derived media is not a public asset grant.
    assets = []
    for p in sorted(ASSETS.rglob('*')):
        if not p.is_file():
            continue
        parts = p.relative_to(ASSETS).parts
        if parts[0] in EXCLUDED | REJECTED or 'Before' in parts or '__pycache__' in parts:
            continue
        if p.suffix.lower() in {'.blend', '.fbx', '.glb', '.png', '.wav', '.json'}:
            assets.append({'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size,
                           'sha256': sha(p.read_bytes())})
    save_json(OUT / 'local-assets.json', {'redistribution': 'Not included; obtain source licenses separately', 'files': assets})
    print(json.dumps({'public_paths': len(selected_files), 'archive_files': len(plan),
                      'archive_bytes': sum(x['bytes'] for x in plan), 'local_asset_records': len(assets)}))


def archive():
    plan = json.loads(text(OUT / 'archive-plan.json'))
    allowed = [(ROOT / 'SourceAssets/SteelWarhammer20261014').resolve(),
               (ROOT / 'Content/Weapons/SteelWarhammer20261014/NormalComboV2').resolve(),
               (ROOT / 'Content/Weapons/SteelWarhammer20261014/NormalComboV3').resolve()]
    for row in plan['files']:
        source, target = (ROOT / row['original']).resolve(), (ROOT / row['destination']).resolve()
        if not any(source.is_relative_to(p) for p in allowed) or not target.is_relative_to(TRASH.resolve()):
            raise RuntimeError('Archive scope escape: ' + str(source))
        if source.is_relative_to(ASSETS.resolve()) and source.relative_to(ASSETS.resolve()).parts[0] in EXCLUDED:
            raise RuntimeError('Parallel stage cannot be archived: ' + str(source))
        if not source.exists() and target.exists() and sha(target.read_bytes()) == row['sha256']:
            continue
        if target.exists() or sha(source.read_bytes()) != row['sha256']:
            raise RuntimeError('Archive collision or source changed: ' + str(source))
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        if source.exists() or target.stat().st_size != row['bytes'] or sha(target.read_bytes()) != row['sha256']:
            raise RuntimeError('Archive readback failed: ' + str(target))
    save_json(OUT / 'archive-manifest.json', {**plan, 'completed': True, 'hash_readback': True})
    save_json(TRASH / 'manifest.json', {**plan, 'completed': True, 'hash_readback': True})
    print('Archived and read back', plan['count'], 'files;', plan['bytes'], 'bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['prepare', 'archive'])
    args = parser.parse_args()
    (prepare if args.operation == 'prepare' else archive)()
