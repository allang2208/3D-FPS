"""Assign and save the style sample while the FPSGAME editor is closed.

Run as a UE Python commandlet. No gameplay, rendering, or validation pass.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2] / 'SourceAssets/FatZombieStyleV1'
MESH = '/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy.SK_FatZombie_Meshy'
MATERIAL = '/Game/Monsters/FatZombieMeshy/StyleV1/MI_FatZombie_Infected_V1.MI_FatZombie_Infected_V1'
ORIGINAL = '/Game/Monsters/FatZombieMeshy/Materials/M_FatZombie_Meshy.M_FatZombie_Meshy'
mesh = u.load_asset(MESH)
material = u.load_asset(MATERIAL)
if mesh is None or material is None:
    raise RuntimeError('The existing FatZombie mesh or completed style material is unavailable.')
slots = mesh.get_editor_property('materials')
previous = None
for index, slot in enumerate(slots):
    if str(slot.material_slot_name) != 'Material_002':
        continue
    previous = slot.material_interface.get_path_name()
    if previous not in [ORIGINAL, MATERIAL]:
        raise RuntimeError('FatZombie material was changed by another task: ' + previous)
    slot.material_interface = material
    slots[index] = slot
    break
if previous is None:
    raise RuntimeError('The expected FatZombie material slot is unavailable.')
mesh.set_editor_property('materials', slots)
if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
    raise RuntimeError('Cannot save the FatZombie material assignment.')
(ROOT / 'activation.json').write_text(json.dumps({
    'revision': '1.0', 'mesh': MESH, 'slot': 'Material_002',
    'previous_material': previous, 'material': MATERIAL,
    'f6_entry': 'FatZombie', 'scope': 'Material slot assignment only',
    'method': 'Offline UE Python commandlet after user closed FPSGAME editor',
    'assets_saved': True, 'runtime_tested': False, 'preview_rendered': False,
}, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('FAT_STYLE_SAMPLE_ACTIVATED')
