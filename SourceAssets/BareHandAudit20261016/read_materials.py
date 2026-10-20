"""Read back the upgraded skin parents (no save)."""
import json, sys
from pathlib import Path
import unreal as u
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareHandAudit20261016'); sys.path.insert(0, str(R))
from skin_recipe import MARK
L = u.MaterialEditingLibrary; E = u.EditorAssetLibrary
rows = []
for row in json.loads((R / 'materials_receipt.json').read_text()):
    pk = row['package']; m = u.load_asset(pk + '.' + pk.split('/')[-1])
    code = str(L.get_material_property_input_node(m, u.MaterialProperty.MP_NORMAL).get_editor_property('code'))
    rows.append(dict(package=pk, upgraded=code.startswith(MARK), tag=E.get_metadata_tag(m, 'BareSkinV8'), expected=('applied' in row)))
    print('BARE_V8_MATERIAL_READ', json.dumps(rows[-1]), flush=True)
(R / 'materials_readback.json').write_text(json.dumps(rows, indent=1))
