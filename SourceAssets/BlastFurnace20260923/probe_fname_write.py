"""Find the write that actually clears a palette entry's Material FName.

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash

Read-only against the palette: it mutates a throwaway copy of the struct on
the Python side only, and reports which assignment forms stick. The skill
notes that enum/Name writes in this build can silently fall back to the
current value, so the working form has to be established before the real edit.
"""
import json
import unreal as u

PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
palette = u.load_asset(PALETTE)
entry = None
for item in palette.get_editor_property('components'):
    if str(item.get_editor_property('id')) == 'blast_furnace':
        entry = item
        break
if entry is None:
    raise RuntimeError('entry missing')

report = {}
trials = [u.Name(''), '', u.Name('none'), u.Name('None')]
for index, trial in enumerate(trials):
    try:
        entry.set_editor_property('material', trial)
        got = entry.get_editor_property('material')
        report['trial_%d' % index] = {
            'set': repr(trial), 'read': repr(got), 'str': str(got),
            'sticks': (str(got) == ''), 'is_none': bool(got.is_none()) if hasattr(got, 'is_none') else None}
    except Exception as error:  # noqa: BLE001
        report['trial_%d' % index] = {'set': repr(trial), 'error': str(error)}
print('FNAME_TRIAL ' + json.dumps(report, ensure_ascii=False), flush=True)
