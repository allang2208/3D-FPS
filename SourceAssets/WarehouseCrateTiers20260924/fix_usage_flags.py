"""In-editor fix (via MCP bridge): M_Crate_* materials were authored for static meshes and lack
the "Used with Skeletal Mesh" usage flag; UE rejects them on the crate SKs and falls back to the
one-sided default material (gray look + backface-culled arch shell). Set the flag, save, report.
"""
import json
import unreal

MAT_DIR = '/Game/Props/WarehouseCrateTiers20260924/Materials/'
NAMES = ['M_Crate_Wood', 'M_Crate_WoodDark', 'M_Crate_Stone', 'M_Crate_Iron',
         'M_Crate_IronDark', 'M_Crate_Gold', 'M_Crate_Silver', 'M_Crate_Gem']
report = {}
for n in NAMES:
    path = MAT_DIR + n
    m = unreal.load_asset(path)
    if m is None:
        report[n] = 'MISSING'
        continue
    before = bool(m.get_editor_property('used_with_skeletal_mesh'))
    if not before:
        m.set_editor_property('used_with_skeletal_mesh', True)
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)  # 强制落盘，无需脏标记
    report[n] = {'was': before, 'now': bool(m.get_editor_property('used_with_skeletal_mesh'))}

with open(r'D:\FPS3D\FPSGAME\SourceAssets\WarehouseCrateTiers20260924\probes\usage_fix.json', 'w', encoding='utf-8') as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)
print('USAGE_FIX_DONE', flush=True)
