"""Read-only: measure every T_Crate_* texture's dimensions/compression/lodgroup.

Writes probes/crate_texture_sizes.json.
"""
import json
import unreal as u

DIR = '/Game/Props/WarehouseCrateTiers20260924/Textures/'
NAMES = ['T_Crate_Wood_Surface', 'T_Crate_Wood_Normal', 'T_Crate_Stone_Surface', 'T_Crate_Stone_Normal',
         'T_Crate_Iron_Surface', 'T_Crate_Iron_Normal', 'T_Crate_Gold_Surface', 'T_Crate_Gold_Normal',
         'T_Crate_Silver_Surface', 'T_Crate_Silver_Normal']
out = {}
for n in NAMES:
    t = u.load_asset(DIR + n)
    if t is None:
        out[n] = 'MISSING'
        continue
    rec = {}
    for prop in ('size_x', 'size_y', 'compression_settings', 'srgb', 'lod_group',
                 'mip_count', 'first_mip_to_generate', 'never_stream'):
        try:
            rec[prop] = str(t.get_editor_property(prop))
        except Exception:
            pass
    try:
        rec['class'] = t.get_class().get_name()
    except Exception:
        pass
    out[n] = rec
with open(r'D:\FPS3D\FPSGAME\SourceAssets\WarehouseCrateTiers20260924\probes\crate_texture_sizes.json', 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print('TEX_SIZES_DONE', flush=True)
