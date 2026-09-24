"""Fresh-process readback: confirm M_Crate_* skeletal-usage + two-sided flags persisted to disk."""
import json
import unreal

MAT_DIR = '/Game/Props/WarehouseCrateTiers20260924/Materials/'
NAMES = ['M_Crate_Wood', 'M_Crate_WoodDark', 'M_Crate_Stone', 'M_Crate_Iron',
         'M_Crate_IronDark', 'M_Crate_Gold', 'M_Crate_Silver', 'M_Crate_Gem']
out = {}
for n in NAMES:
    m = unreal.load_asset(MAT_DIR + n)
    if m is None:
        out[n] = 'MISSING'
        continue
    out[n] = {'skeletal': bool(m.get_editor_property('used_with_skeletal_mesh')),
              'two_sided': bool(m.get_editor_property('two_sided'))}
all_ok = all(isinstance(v, dict) and v['skeletal'] and v['two_sided'] for v in out.values())
out['ALL_OK'] = all_ok
with open(r'D:\FPS3D\FPSGAME\SourceAssets\WarehouseCrateTiers20260924\probes\usage_readback.json', 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print('USAGE_READBACK_DONE', flush=True)
