"""Build reviewable, task-only Git blobs without rewriting shared working files."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
REVIEW = OUT / 'Local/review'
ID = 'ue_rsh12'


def git(*args, data=None):
    return subprocess.run(['git', *args], cwd=ROOT, input=data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout


def head(path):
    return git('show', 'HEAD:' + path).decode('utf-8-sig')


def working(path):
    return (ROOT / path).read_text(encoding='utf-8-sig').replace('\r\n', '\n')


def own_runtime(path):
    """Select zero-context owned edits; remove added Pit Viper terms from mixed lines."""
    original = head(path).splitlines(keepends=True)
    diff = git('diff', '--unified=0', '--', path).decode('utf8')
    matches = list(re.finditer(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n', diff, re.M))
    markers = ('RSH12', 'RSH-12', 'ue_rsh12', 'SampleRSH12Presentation', 'IsSingleActionCocking',
               'SightLayer', 'SetSharedClipsFromJson', 'MagazineCapacity', 'H.Stats.Capacity',
               'W.Base.Capacity', '(IsWeaponBusy() && !IsRevolverFireActionPlaying())')
    edits = []
    for i, match in enumerate(matches):
        chunk = diff[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(diff)]
        old = ''.join(line[1:] for line in chunk.splitlines(keepends=True) if line.startswith('-'))
        new = ''.join(line[1:] for line in chunk.splitlines(keepends=True) if line.startswith('+'))
        selected = any(marker in chunk for marker in markers)
        if path.endswith('PistolDualWieldComponent.cpp') and 'for(const TCHAR* Family:{TEXT("base")' in new:
            selected = True
        if not selected:
            continue
        if 'ue_pit_viper2011' in new and 'ue_pit_viper2011' not in old:
            new = re.sub(r'\|\|(?:I(?:->|\.)Definition|Item\.Definition)==TEXT\("ue_pit_viper2011"\)', '', new)
            new = re.sub(r'&&Item\.Definition!=TEXT\("ue_pit_viper2011"\)', '', new)
            if 'ue_pit_viper2011' in new:
                raise RuntimeError('Mixed non-RSH addition needs review: ' + path)
        start, count = int(match[1]), int(match[2] or 1)
        pos = start if count == 0 else start - 1
        if ''.join(original[pos:pos + count]) != old:
            raise RuntimeError('Original hunk differs: ' + path)
        edits.append((pos, count, new.splitlines(keepends=True)))
    for pos, count, lines in reversed(edits):
        original[pos:pos + count] = lines
    return ''.join(original)


def insert_object(text, key, value):
    """Replace/add one dictionary member while preserving all other serialized members."""
    data = json.loads(text)
    encoded = json.dumps(value, ensure_ascii=False, indent=2)
    if key in data:
        match = re.search(re.escape(json.dumps(key, ensure_ascii=False)) + r'\s*:\s*', text)
        start = match.end()
        _, length = json.JSONDecoder().raw_decode(text[start:])
        return text[:start] + encoded + text[start + length:]
    end = text.rfind('}')
    return text[:end].rstrip() + (',\n' if data else '\n') + json.dumps(key, ensure_ascii=False) + ': ' + encoded + '\n' + text[end:]


def nested_object(text, parent, values):
    match = re.search(re.escape(json.dumps(parent)) + r'\s*:\s*', text)
    start = match.end()
    _, length = json.JSONDecoder().raw_decode(text[start:])
    region = text[start:start + length]
    for key, value in values.items():
        region = insert_object(region, key, value)
    return text[:start] + region + text[start + length:]


def main(stage):
    if git('diff', '--cached', '--name-only').strip():
        raise RuntimeError('Existing staged work retained; do not mix commits')
    tip = git('rev-parse', 'HEAD').decode().strip()
    content = {}
    integrations = [ROOT / 'SourceAssets' / name for name in (
        'RSH12Integration20261003', 'RSH12SingleAction20261003')]
    runtime = set(json.loads((integrations[0] / 'runtime_edits.json').read_text())['modified'])
    runtime.update(json.loads((integrations[1] / 'runtime_edits.json').read_text())['files'])
    runtime.update(['Source/FPSGAME/Weapons/WeaponGripProfile.cpp', 'Source/FPSGAME/Weapons/WeaponGripProfile.h'])
    runtime.discard('Config/DefaultGame.ini')
    runtime.discard('Source/FPSGAME/Weapons/RSH12WeaponAssets.h')
    for path in sorted(runtime):
        candidate = own_runtime(path)
        if candidate != head(path):
            content[path] = candidate
    for path in ('Source/FPSGAME/Weapons/RSH12WeaponAssets.h', 'Source/FPSGAME/Weapons/RSH12Presentation.cpp'):
        content[path] = working(path)

    path = 'Config/DefaultGame.ini'
    content[path] = head(path).rstrip() + '\n\n[/Script/UnrealEd.ProjectPackagingSettings]\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/RSH12")\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/AnimationProfiles20261001/ue_rsh12")\n+DirectoriesToAlwaysStageAsUFS=(Path="ColdSteelData/Licenses")\n'
    for path in ('Content/ColdSteelData/items.json', 'Content/ColdSteelData/combat-weapon-formulas.json'):
        content[path] = insert_object(head(path), ID, json.loads(working(path))[ID])
    path = 'Content/ColdSteelData/gunsmith.json'
    value = next(row for row in json.loads(working(path))['weapons'] if row['id'] == ID)
    text = head(path)
    match = re.search(r'"weapons"\s*:\s*', text)
    start = match.end()
    rows, length = json.JSONDecoder().raw_decode(text[start:])
    if any(row['id'] == ID for row in rows):
        raise RuntimeError('RSH already published; reconcile the exact entry')
    end = start + length - 1
    content[path] = text[:end].rstrip() + (',\n' if rows else '\n') + json.dumps(value, ensure_ascii=False, indent=2) + '\n' + text[end:]
    path = 'Content/ColdSteelData/modular_outfits.json'
    profiles = json.loads(working(path))['profiles']
    content[path] = nested_object(head(path), 'profiles', {key: value for key, value in profiles.items() if '/Weapons/RSH12/' in key})

    path = '.gitignore'
    text = working(path)
    start = text.index('# RSH-12 pause:')
    last = '!/SourceAssets/RSH12Publication20261003/published-files.json'
    end = text.index(last, start) + len(last)
    content[path] = head(path).rstrip() + '\n\n' + text[start:end] + '\n'
    path = 'Docs/Backlog.md'
    text = working(path)
    start = text.index('## RSH-12 握持与单动拨锤')
    end = text.index('\n## ', start + 3)
    section = text[start:end]
    original = head(path)
    first = original.index('\n')
    content[path] = original[:first + 1] + '\n' + section + '\n' + original[first + 1:]
    path = 'Docs/AssetSetup.md'
    text = working(path)
    start = text.index('## RSH-12：')
    end = text.find('\n## ', start + 3)
    content[path] = head(path).rstrip() + '\n\n' + text[start:end if end >= 0 else len(text)]
    for skill, ref, anchor in (
        ('ue5-weapon-workflow', 'revolver-mechanical-binding.md', '## 按任务读取'),
        ('ue5-fps-arms-animation', 'revolver-grip-cock.md', '## 按问题读取')):
        path = 'skills/' + skill + '/SKILL.md'
        line = next(line for line in working(path).splitlines() if ref in line)
        content[path] = head(path).replace(anchor + '\n', anchor + '\n\n' + line + '\n', 1)

    tasks = ('RSH12Integration20261003', 'RSH12SingleAction20261003', 'RSH12Fit20261003',
             'RSH12FireFix20261003', 'RSH12Grip20261003', 'RSH12Publication20261003')
    for task in tasks:
        directory = ROOT / 'SourceAssets' / task
        for file in directory.iterdir():
            if file.is_file() and file.suffix in ('.py', '.ps1', '.md'):
                path = file.relative_to(ROOT).as_posix()
                content[path] = file.read_text(encoding='utf8').replace('\r\n', '\n')
    author_parameters = ['SourceAssets/RSH12Integration20261003/production_recipe.json',
                         'SourceAssets/RSH12Fit20261003/fit_contract.json',
                         'SourceAssets/RSH12Grip20261003/grip_registration.json']
    for pattern in ('hand_contact_*.json', 'cock_contact_*.json', 'trigger_contact_*.json'):
        author_parameters.extend(file.relative_to(ROOT).as_posix() for file in (ROOT / 'SourceAssets/RSH12Grip20261003').glob(pattern))
    for path in author_parameters:
        content[path] = working(path)
    for file in (ROOT / 'Docs/Weapons').glob('rsh12*20261003.md'):
        path = file.relative_to(ROOT).as_posix()
        content[path] = working(path)
    for path in ('Docs/ThirdParty/RSH12-Medji-CCBY4.md',
                 'skills/ue5-weapon-workflow/references/revolver-mechanical-binding.md',
                 'skills/ue5-fps-arms-animation/references/revolver-grip-cock.md',
                 'SourceAssets/RSH12Publication20261003/archive-manifest.json',
                 'SourceAssets/RSH12Publication20261003/retained-recovery-dependencies.json'):
        content[path] = working(path)

    manifest = dict(task='RSH-12 paused source publication', base_commit=tip,
                    scope='Exact RSH source edits; unrelated working changes preserved',
                    latest_grip_source_revision='registered-mechanical-axes-v3-full-skin',
                    latest_fire_source_baked=False, latest_grip_assets_saved=False,
                    new_game_tests=False,
                    files=[dict(path=path, bytes=len(text.encode('utf8')),
                                sha256=hashlib.sha256(text.encode('utf8')).hexdigest())
                           for path, text in sorted(content.items())])
    manifest_path = 'SourceAssets/RSH12Publication20261003/published-files.json'
    content[manifest_path] = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    (ROOT / manifest_path).write_text(content[manifest_path], encoding='utf8')
    for path, text in content.items():
        destination = REVIEW / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(text.encode('utf8'))
    if stage:
        if git('rev-parse', 'HEAD').decode().strip() != tip or git('diff', '--cached', '--name-only').strip():
            raise RuntimeError('Git state changed during preparation')
        records = []
        for path, text in sorted(content.items()):
            blob = git('hash-object', '-w', '--stdin', data=text.encode('utf8')).decode().strip()
            records.append('100644 ' + blob + '\t' + path + '\n')
        git('update-index', '--index-info', data=''.join(records).encode('utf8'))
    print(json.dumps(dict(files=len(content), bytes=sum(len(text.encode('utf8')) for text in content.values()),
                          review=str(REVIEW), staged=stage)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', action='store_true')
    main(parser.parse_args().stage)
