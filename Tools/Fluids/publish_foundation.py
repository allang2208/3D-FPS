"""Copy only newly authored fluid packages into FPSGAME, without replacing assets.

Run after all four authoring stages have finished saving. Existing differing
packages stop publication: use the running editor for subsequent asset edits.
This records file delivery, not runtime or visual verification.
"""
import json
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / 'SourceAssets' / 'FluidFoundation20260923'
AUTHOR_CONTENT = SOURCE / 'UEAuthoring' / 'Content'
CONTENT = PROJECT / 'Content'
records = []

for stage in ('templates', 'volume', 'liquid', 'water'):
    paths = json.loads((SOURCE / ('ue-' + stage + '-saved.json')).read_text(encoding='utf-8'))
    for object_path in dict.fromkeys(paths):
        package = object_path.split('.', 1)[0]
        if not package.startswith('/Game/Fluids/Foundation/'):
            raise RuntimeError('Package outside this task: ' + package)
        relative = Path(package.removeprefix('/Game/') + '.uasset')
        source_file = AUTHOR_CONTENT / relative
        for extension in ('.uasset', '.uexp', '.ubulk', '.uptnl'):
            src = source_file.with_suffix(extension)
            if not src.is_file():
                if extension == '.uasset':
                    raise FileNotFoundError(src)
                continue
            dst = (CONTENT / relative).with_suffix(extension)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                if dst.read_bytes() != src.read_bytes():
                    raise RuntimeError('Existing package differs; not overwritten: ' + str(dst))
            else:
                with src.open('rb') as incoming, dst.open('xb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
            records.append({'asset': object_path, 'file': str(dst), 'bytes': dst.stat().st_size})

receipt = {'status': 'assets_saved_and_copied', 'files': records,
           'editor_restart': 'New plugin settings take effect on next normal project launch',
           'gameplay_replacement': False, 'runtime_tested': False, 'visually_tested': False,
           'zibravdb': 'Optional backend not installed; native SVT route is authored'}
(SOURCE / 'delivery.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('FLUID_FOUNDATION_DELIVERED', len(records), 'files')
print(SOURCE / 'delivery.json')
