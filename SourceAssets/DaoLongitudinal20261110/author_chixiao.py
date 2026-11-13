"""Save widened crimson textures and an editable copy without mesh changes."""
import json
import runpy
from pathlib import Path
import bpy

P = Path(__file__).resolve().parent
SOURCE = P.parent / 'Zhanmadao20261018/ChixiaoBladeV1'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'Chixiao_Blade_Editable.blend'))
bpy.context.preferences.filepaths.save_version = 0
maps = runpy.run_path(str(P / 'chixiao_surface.py'))['build_maps']()
(P / 'Textures').mkdir(exist_ok=True)
for key, pixels in maps.items():
    name = 'Chixiao_' + key
    image = bpy.data.images.get(name)
    if image is None:
        raise RuntimeError('Missing authored image ' + name)
    image.pixels.foreach_set(pixels.astype('float32').ravel())
    image.filepath_raw = str(P / 'Textures' / (name + '_LongitudinalV2.png'))
    image.file_format = 'PNG'
    image.save()
    image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'Chixiao_LongitudinalV2_Editable.blend'))
(P / 'chixiao-production.json').write_text(json.dumps({
    'ribbon_u_old': [.052, .128], 'ribbon_u_mid_new': [.048, .265],
    'rune_lane_u': [.36, .82], 'geometry_changed': False,
    'saved_maps': list(maps), 'game_tested': False}, indent=2) + '\n', encoding='utf-8')
print('CHIXIAO_LONGITUDINAL_TEXTURES_AUTHORED')
