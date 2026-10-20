"""Precise staging for the V9 rollout publish (WORKFLOW.md section 8).

Whole files that are entirely this task's work are `git add`ed. Files mixed with other sessions' edits
(AGENTS.md, Docs/Backlog.md, FPSGAMECharacter.cpp) are staged by replaying only this task's changes onto
the HEAD blob via hash-object + update-index --cacheinfo; the working tree keeps everyone's edits.
"""
import subprocess
from pathlib import Path

P = Path('D:/FPS3D/FPSGAME')
R = 'SourceAssets/BareSkinV9Rollout_20261017'


def git(*args, inp=None):
    r = subprocess.run(['git', '-C', str(P), *args], input=inp, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace')[:400]}")
    return r.stdout


def head(path):
    return git('show', f'HEAD:{path}').decode('utf-8')


def work(path):
    return (P / path).read_text(encoding='utf-8')


def stage_blob(path, text):
    sha = git('hash-object', '-w', '--stdin', inp=text.encode('utf-8')).decode().strip()
    git('update-index', '--cacheinfo', f'100644,{sha},{path}')
    print(f'staged-blob {path} -> {sha[:10]}')


TO_ADD = []


def add(path):
    TO_ADD.append(path)


def flush():
    ignored = set()
    for i in range(0, len(TO_ADD), 300):
        r = subprocess.run(['git', '-C', str(P), 'check-ignore', *TO_ADD[i:i + 300]], capture_output=True)
        ignored.update(p for p in r.stdout.decode('utf-8').splitlines() if p)
    batch = [p for p in TO_ADD if p not in ignored]
    for i in range(0, len(batch), 300):
        git('add', '--', *batch[i:i + 300])
    print(f'staged {len(batch)} files (ignored {len(ignored)})')
    TO_ADD.clear()


# ---------- 1. whole files that are entirely this task's ----------

for p in [
    'Docs/Characters/bare-palm-hole-repair-20261014.md',
    'Docs/Characters/bare-skin-v9-m4-sample-20261017.md',
    'Docs/Characters/bare-skin-v9-rollout-20261017.md',
    'Docs/Characters/bare-surface-v8-20261016.md',
    'Docs/Characters/bare-palm-native-default-v7-20260925.md',
    'Docs/Weapons/super90-speedloader-r26-push-flick-20261016.md',
    'Docs/Weapons/super90-speedloader-r27-align-drive-20261016.md',
    'Source/FPSGAME/Characters/FPSArmJointCorrectiveComponent.h',
    'Source/FPSGAME/Characters/FPSArmJointCorrectiveComponent.cpp',
    'skills/ue5-fps-arms-animation/references/accepted-bare-hands.md',
    'skills/ue5-fps-arms-animation/references/super90-shared-clock.md',
]:
    add(p)

# rollout dir: top-level files + receipt dirs (json only); big data dirs stay untracked/local
roll = P / R
for f in sorted(roll.iterdir()):
    if f.is_file():
        add(f'{R}/{f.name}')
    elif f.name.startswith('Installed'):
        for j in sorted(f.rglob('*.json')):
            add(str(j.relative_to(P)).replace('\\', '/'))

# other task dirs: text sources under 1 MB
for d in ['BareHandAudit20261016', 'BarePalmHoleRepair20261014', 'BareSkinUpgradePlan20261017',
          'BareSkinV9M4_20261017', 'Super90LoaderR26_20261016', 'Super90LoaderR27_20261016']:
    for f in sorted((P / 'SourceAssets' / d).rglob('*')):
        if f.is_file() and f.stat().st_size < 1_000_000 and \
                f.suffix.lower() in {'.py', '.ps1', '.md', '.txt', '.json', '.ini', '.cfg', '.csv', '.hlsl', '.bat', '.cmd', '.fx'}:
            add(str(f.relative_to(P)).replace('\\', '/'))

flush()

# ---------- 2. replay this task's hunks onto HEAD for mixed files ----------

# AGENTS.md: replace the V7 hand-model baseline paragraph with the V9 one
old = head('AGENTS.md').splitlines(keepends=True)
new = work('AGENTS.md').splitlines(keepends=True)
old_p = next(i for i, l in enumerate(old) if l.startswith('**第一人称手模基准'))
new_p = next(i for i, l in enumerate(new) if l.startswith('**第一人称手模基准'))
out = old[:old_p] + [new[new_p]] + old[old_p + 1:]
stage_blob('AGENTS.md', ''.join(out))

# Docs/Backlog.md: insert this task's sections at the top
hb = head('Docs/Backlog.md').splitlines(keepends=True)
wb = work('Docs/Backlog.md').splitlines(keepends=True)


def section(lines, marker, end_marker):
    i = next(i for i, l in enumerate(lines) if l.startswith(marker))
    j = next(j for j in range(i + 1, len(lines)) if lines[j].startswith(end_marker))
    while j > i and lines[j - 1].strip() == '':
        j -= 1
    return lines[i:j]


mine = []
mine += section(wb, '## 裸手 V9 推广', '## 裸手 V9：M4')
mine += ['\n']
mine += section(wb, '## 裸手 V9：M4', '## 裸手表面 V8')
mine += ['\n']
mine += section(wb, '## 裸手表面 V8', '## Super90 源装备')
mine += ['\n']
mine += section(wb, '## Super90 快速装填对准', '## Super90 快速装填推进解焊')
mine += ['\n']
mine += section(wb, '## Super90 快速装填推进解焊', '## Super90 快速装填节奏')
mine += ['\n']

# HEAD starts with "# 待办事项（未做清单）" then a blank line; insert before the first "## "
ins = next(i for i, l in enumerate(hb) if l.startswith('## '))
out = hb[:ins] + mine + hb[ins:]
stage_blob('Docs/Backlog.md', ''.join(out))

# FPSGAMECharacter.cpp: add include + CreateDefaultSubobject for the corrective component
fc = head('Source/FPSGAME/FPSGAMECharacter.cpp')
inc_anchor = '#include "Characters/FPSModularOutfitComponent.h"'
assert inc_anchor in fc
fc = fc.replace(inc_anchor, inc_anchor + '\n#include "Characters/FPSArmJointCorrectiveComponent.h"', 1)
ctor_anchor = 'CreateDefaultSubobject<UFPSModularOutfitComponent>(TEXT("ModularOutfit"));'
assert ctor_anchor in fc
fc = fc.replace(ctor_anchor, ctor_anchor + '\n    CreateDefaultSubobject<UFPSArmJointCorrectiveComponent>(TEXT("ArmJointCorrective"));', 1)
stage_blob('Source/FPSGAME/FPSGAMECharacter.cpp', fc)

print('done')
