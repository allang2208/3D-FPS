"""Bake the project's semibold face for UE TextRender. Run in a private Windows authoring host."""
import ctypes
import json
import os
import re
from pathlib import Path

import unreal as u

project = Path(os.environ['FPS_TEXT_PROJECT'])
batch = Path(os.environ['FPS_TEXT_BATCH'])
if Path(u.Paths.project_dir()).resolve() != (batch / 'Host').resolve():
    raise RuntimeError('Expected the private font authoring host')

face = project / 'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-SemiBold.ttf'
characters = set(chr(i) for i in range(32, 127))

def collect(value):
    if isinstance(value, str):
        characters.update(c for c in value if '\u3000' <= c <= '\u9fff' or '\uff01' <= c <= '\uffef')
    elif isinstance(value, dict):
        for item in value.values():
            collect(item)
    elif isinstance(value, list):
        for item in value:
            collect(item)

for data in (project / 'Content/ColdSteelData').rglob('*.json'):
    collect(json.loads(data.read_bytes()))
for source in (project / 'Source/FPSGAME').rglob('*'):
    if source.suffix not in {'.cpp', '.h', '.inl'} or any(key in source.name for key in ('Audit', 'Review', 'Commandlet')):
        continue
    collect(re.findall(r'(?:TEXT|INVTEXT)\("([^"\n]*)"\)', source.read_text(encoding='utf-8-sig')))
characters.update('°·–—±×％…→←')

# GDI font selection is local to this process. Use the exact static face used by Slate.
gdi = ctypes.windll.gdi32
if not gdi.AddFontResourceExW(str(face), 0x10, None):
    raise RuntimeError(f'Cannot load {face}')
try:
    factory = u.TrueTypeFontFactory()
    options = factory.get_editor_property('import_options')
    data = options.get_editor_property('data')
    settings = dict(font_name='Noto Sans SC SemiBold', height=32., chars=''.join(sorted(characters)),
                    include_ascii_range=True, use_distance_field_alpha=True, distance_field_scale_factor=4,
                    distance_field_scan_radius_scale=.35, texture_page_width=1024, texture_page_max_height=1024,
                    x_padding=5, y_padding=5)
    for key, value in settings.items():
        data.set_editor_property(key, value)
    options.set_editor_property('data', data)
    folder = '/Game/UI/GunsmithWorkbench/WorldText'
    font = u.AssetToolsHelpers.get_asset_tools().create_asset('F_ColdSteelWorldText', folder, u.Font, factory)
    if not font or not u.EditorAssetLibrary.save_loaded_asset(font, False):
        raise RuntimeError('World font was not saved')
    receipt = dict(package=font.get_path_name(), source=face.name, characters=''.join(sorted(characters)),
                   height=settings['height'], distance_field=True)
    (batch/'world-font.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    print('SAVED_WORLD_TEXT',receipt['package'],len(characters))
finally:
    gdi.RemoveFontResourceExW(str(face), 0x10, None)
