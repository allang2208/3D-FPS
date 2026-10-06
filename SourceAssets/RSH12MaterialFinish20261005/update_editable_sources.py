"""Background author-source updates only; no renders or model rebuilding."""
import json
import runpy
import shutil
from pathlib import Path
import bpy

O = Path(__file__).resolve().parent
S = O.parent
helper = runpy.run_path(str(O / 'finish_blender.py'))
bpy.context.preferences.filepaths.save_version = 0
saved = []

def open_source(path):
    dest = O / 'BeforeSources/SourceAssets' / path.relative_to(S)
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    bpy.ops.wm.open_mainfile(filepath=str(path))

def save_source(path):
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    saved.append(str(path))

for key in ('vertical', 'tactical_vertical', 'canted', 'prism', 'angled'):
    path = S / 'RSH12Foregrips20261004/Exports' / ('SM_RSH12_' + key + '_Editable.blend')
    open_source(path)
    helper['foregrip_materials'](bpy.data.objects['SM_RSH12_' + key])
    save_source(path)

path = S / 'RSH12QuickDrawGrip20261005/RSH12_QuickDrawGrip_Editable.blend'
open_source(path)
for image in bpy.data.images:
    if 'QuickDrawGrip_GraphiteFrame_ORM' in image.name:
        image.filepath = str(S / 'RSH12QuickDrawGrip20261005/Textures/T_RSH12_QuickDrawGrip_GraphiteFrame_ORM.png')
        image.reload()
save_source(path)

author = json.loads((S / 'RSH12CubeSuppressor20261004/authoring.json').read_text())
for path in dict.fromkeys([Path(author['blend']), Path(author['placement_source'])]):
    open_source(path)
    for m in bpy.data.materials:
        if m.name.startswith('RSH12Cube_Recess') and m.use_nodes:
            for node in m.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    node.inputs['Metallic'].default_value = 0.
    save_source(path)

(O / 'editable_source_receipt.json').write_text(json.dumps({'saved':saved,'rendered':False},indent=2))
print('RSH_EDITABLE_MATERIALS_SAVED', len(saved), flush=True)
