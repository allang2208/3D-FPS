"""Plan this paused RSH task's retired files; native PowerShell performs moves."""
from pathlib import Path
import hashlib
import json

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
TRASH = ROOT / 'trash/rsh12-pause-20261003'
TASKS = [ROOT / 'SourceAssets' / name for name in (
    'RSH12Integration20261003', 'RSH12SingleAction20261003',
    'RSH12Fit20261003', 'RSH12FireFix20261003', 'RSH12Grip20261003')]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    target = OUT / 'archive-manifest.json'
    if target.exists():
        raise RuntimeError('Archive plan already exists; retain it for recovery')
    retired = {}

    def add(path, reason, replacement):
        path = path.resolve()
        if not any(path.is_relative_to(task.resolve()) for task in TASKS):
            raise RuntimeError('Out-of-task source')
        if not path.is_file():
            return
        rel = path.relative_to(ROOT).as_posix()
        destination = (TRASH / rel).resolve()
        if not destination.is_relative_to(TRASH.resolve()):
            raise RuntimeError('Out-of-trash destination')
        if destination.exists():
            raise RuntimeError('Archive destination exists: ' + rel)
        retired[rel] = dict(original=rel, archived=destination.relative_to(ROOT).as_posix(),
                            bytes=path.stat().st_size, sha256=digest(path),
                            reason=reason, replacement=replacement)

    grip = TASKS[-1]
    keep_logs = {
        'build_editor_02.log', 'build_editor_03.log', 'build_editor_03_console.log',
        'author_held_single_stablegrasp.log', 'author_held_r_absolute.log',
        'author_held_l_stablegrasp.log', 'fit_held_l_idle_seed.log',
        'fit_held_r_idle_nativejoint.log', 'fit_held_single_aim_nativejoint.log',
        'fit_held_single_idle_nativejoint.log',
        'fit_cock_single_absolutegrasp.log', 'fit_cock_r_absolutegrasp.log',
        'fit_cock_l_absolutegrasp.log', 'fit_trigger_single_idle_reach.log',
        'fit_trigger_single_aim_reach.log', 'fit_trigger_r_idle_reach.log',
        'fit_trigger_l_idle_reach.log', 'compare_held_profile_absolute.log'}
    old_results = {
        'action_inspection.json', 'cock_surface_contacts.json', 'grip_after.json',
        'hand_contact.json', 'registration_candidates.json', 'import_receipt_initial.json',
        'compile_bridge_01.json', 'end_pie_bridge_01.json', 'import_bridge_02.json',
        'build_editor.json', 'build_editor_02.json'}
    for path in grip.iterdir():
        if path.is_file() and (path.suffix == '.png'
                or (path.suffix == '.log' and path.name not in keep_logs)
                or path.name in old_results):
            add(path, 'Superseded grip/cock experiment or failed transport attempt',
                'Current author sources/contact recipes; latest source is unbaked, see pause document')

    single_action = TASKS[1]
    for family in ('single', 'r', 'l'):
        for path in (single_action / family).iterdir():
            if path.is_file():
                add(path, 'Fire/cock bake precedes latest complete-skin, common-grasp and thumb-path source',
                    'author_single_action.py; regenerate four clips and three profiles before importing')
    for task in TASKS[:2]:
        for path in task.rglob('*.blend1'):
            if not any(part.startswith('Before') for part in path.relative_to(task).parts):
                add(path, 'Superseded automatic Blender backup', 'Current editable source and retained BeforeAuthored')

    integration = TASKS[0]
    obsolete = {
        'bind_failure.log', 'failed_parent_r.json', 'failed_parent_single.json',
        'read_bind_failure.py', 'read_fbx_binding.py'}
    for path in integration.iterdir():
        if path.is_file() and (path.name in obsolete or path.name.startswith('import_assets-backup-')):
            add(path, 'Rejected FBX parent-bind/import attempt; corrected full native binding retained',
                'author_rsh12.py, binding_inputs.py and import_assets.py')

    data = dict(task='RSH-12 pause 2026-10-03', state='planned',
                trash=TRASH.relative_to(ROOT).as_posix(),
                count=len(retired), bytes=sum(row['bytes'] for row in retired.values()),
                entries=[retired[key] for key in sorted(retired)])
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({key: data[key] for key in ('state', 'count', 'bytes', 'trash')}))


if __name__ == '__main__':
    main()
