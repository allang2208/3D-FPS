"""Publish saved UI textures and PNGs first, then change only this bow's icon mappings."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

root, batch = map(Path, sys.argv[1:])
author = Path(__file__).resolve().parent
rel = Path('Content/ColdSteelData/AttachmentIcons20260913/FramedBows')
catalog = root / 'Content/ColdSteelData/bow-gunsmith.json'
prefix = 'bow_frontier_compound_'
slots = ('riser', 'grip', 'arrow_rest', 'string', 'stabilizer')
factory = {s: prefix + s + '_false_r3' for s in slots}
category = dict(factory, sight=prefix + 'category_sight_r3')
factory['sight'] = 'bow_dark_sight_no_sight'
saved = json.loads((batch / 'saved-textures.json').read_text())
expected = set(category.values())
if expected != set(saved):
    raise ValueError('Saved texture keys do not match this bow')
sources = {}
for key in sorted(expected):
    for ext, directory in [('.png', author / 'Export'), ('.uasset', batch / 'Host' / rel)]:
        filename = key + ext
        source = directory / filename
        if not source.is_file() or not source.stat().st_size:
            raise FileNotFoundError(source)
        sources[filename] = source

def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()

installed = {}
for filename, source in sources.items():
    target = root / rel / filename
    checksum = digest(source)
    if target.exists() and digest(target) != checksum:
        raise FileExistsError(f'{target} already belongs to a different version')
    if not target.exists():
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp:
            with source.open('rb') as original:
                shutil.copyfileobj(original, temp)
        os.replace(temp.name, target)
    installed[filename] = checksum
# Re-read after the copies so concurrent changes to other bow properties survive.
original = catalog.read_bytes()
data = json.loads(original)
def rows(value):
    if isinstance(value, list):
        for row in value:
            yield from rows(row)
    elif isinstance(value, dict):
        if value.get('id') == 'bow_frontier_compound' and 'factory_icon_sources' in value:
            yield value
        else:
            for child in value.values():
                yield from rows(child)
bow, = rows(data)
text = original.decode('utf-8')
newlines = '\r\n' if '\r\n' in text else '\n'
for name, new in [('category_icon_sources', category), ('factory_icon_sources', factory)]:
    old = bow[name]
    before = '      "' + name + '": ' + json.dumps(old, ensure_ascii=False, indent=2).replace('\n', '\n      ')
    after = '      "' + name + '": ' + json.dumps({k:new.get(k,v) for k,v in old.items()}, ensure_ascii=False, indent=2).replace('\n', '\n      ')
    before = before.replace('\n', newlines)
    after = after.replace('\n', newlines)
    if text.count(before) != 1:
        raise ValueError(f'Cannot uniquely match {name} for this bow')
    text = text.replace(before, after, 1)
if text.encode('utf-8') != original:
    with tempfile.NamedTemporaryFile(dir=catalog.parent, delete=False) as temp:
        temp.write(text.encode('utf-8'))
    if catalog.read_bytes() != original:
        Path(temp.name).unlink()
        raise RuntimeError('Catalog changed during install, retry')
    os.replace(temp.name, catalog)
receipt = {'bow': 'bow_frontier_compound', 'factory': factory, 'category': category, 'published_ui_files': installed,
           'runtime_directory': str(root / rel), 'author':str(author), 'previous_version':str(batch / 'Before'),
           'saved_packages': saved, 'animation_source': ['Weapons/Bow/BowArmsMeshComponent.cpp',
           'Weapons/Bow/BowPresentation.cpp', 'Weapons/Bow/BowRelease.cpp', 'Weapons/Bow/BowFlexMeshComponent.cpp',
           'Weapons/Bow/BowArrow.cpp', 'Weapons/Bow/BowArrow.h', 'Weapons/Bow/BowWeaponComponent.h',
           'Weapons/Bow/BowMountainEchoArrow.cpp','Characters/FPSPlayerBodyBow.cpp'],
           'gameplay_tested':False}
record = batch / 'published.json'
previous = json.loads(record.read_text(encoding='utf-8')) if record.exists() else {}
previous.update(receipt)
record.write_text(json.dumps(previous, ensure_ascii=False, indent=2), encoding='utf-8')
